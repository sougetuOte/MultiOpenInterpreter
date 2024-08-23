import logging
import signal
import sys
from functools import lru_cache
import json
import os
from typing import List, Tuple
from interpreter import OpenInterpreter
from dotenv import load_dotenv

# .env ファイルから環境変数を読み込む
load_dotenv()

# 設定ファイルの読み込み
with open('config.json', 'r') as f:
    CONFIG = json.load(f)

# ロギングの設定
logging.basicConfig(level=CONFIG['log_level'], format='%(asctime)s - %(levelname)s - %(message)s', filename=CONFIG['log_file'])

class Agent:
    def __init__(self, name: str, personality: str, expertise: str, role: str, priority: int, is_coordinator: bool = False):
        self.name = name
        self.personality = personality
        self.expertise = expertise
        self.role = role
        self.priority = priority
        self.interpreter = OpenInterpreter()
        self.interpreter.api_key = os.getenv('OPENAI_API_KEY')
        self.interpreter.model = CONFIG['coordinator_model'] if is_coordinator else CONFIG['agent_model']
        self.interpreter.auto_run = CONFIG['auto_run']
        self.interpreter.debug_mode = CONFIG['debug_mode']
        self.interpreter.local = CONFIG['local']
        self.interpreter.require_user_approval = CONFIG['require_user_approval']
        self.task_completed = False
        self.last_topic = ""
        
        self.interpreter.system_message = f"""
{name}({personality}, {expertise}専門家): {role}として以下を厳守:
1. 質問に簡潔・正確に回答。不確実な場合は明示。
2. 必要に応じて他エージェントの補足を具体的に要請。
3. {expertise}関連の情報のみ提供。
4. 議論の十分性とまとめ可能性を判断・伝達。
5. 回答の一貫性を保持。
6. タスクが完了したと判断した場合は、「タスク完了」または「要件満たす」と明記してください。
7. 常に現在のトピックに関連する情報のみを提供してください。
Pythonコード実行可能。ファイルシステムアクセス可能。
"""
        if is_coordinator:
            self.interpreter.system_message += """
コーディネーターとして全体を統括し、議論を効果的に管理。
1. 各エージェントの「タスク完了」や「要件満たす」などの報告を注意深く監視し、
   全エージェントがタスクを完了したと報告した場合は、議論の終了を提案してください。
2. 各ラウンドで扱うべきトピックを明確に指定し、必要に応じて次の発言者を指名してください。
3. 議論が脱線しないよう、トピックの管理を行ってください。
4. 応答の中に以下の情報を含めてください：
   - トピック: [現在のトピック]
   - 次の発言者: [エージェント名]（必要な場合のみ）
"""

    def respond(self, query: str, context: str = "", topic: str = "") -> str:
        self.last_topic = topic
        full_query = f"{context}\n\nトピック: {topic}\n\nユーザーの質問: {query}\n\nあなたの回答:"
        try:
            response = self.interpreter.chat(full_query, display=False)
            
            if self.interpreter.require_user_approval and response[-1].get('command'):
                print(f"\n実行予定のコマンド: {response[-1]['command']}")
                if input("このコマンドを実行しますか？ (y/n): ").lower().strip() != 'y':
                    return "コマンドの実行がキャンセルされました。"
            
            content = response[-1]['content'] if response else "応答がありませんでした。"
            self.task_completed = "タスク完了" in content or "要件満たす" in content
            return content
        except Exception as e:
            logging.error(f"エージェント {self.name} の応答中にエラー: {str(e)}")
            return f"エラーが発生しました: {str(e)}"

    def cleanup(self):
        try:
            if hasattr(self.interpreter, 'cleanup'):
                self.interpreter.cleanup()
            elif hasattr(self.interpreter, 'kernel') and self.interpreter.kernel:
                self.interpreter.kernel.cleanup()
        except Exception as e:
            logging.error(f"エージェント {self.name} のクリーンアップ中にエラー: {str(e)}")

class AgentTeam:
    def __init__(self, agents: List[Agent]):
        self.agents = sorted(agents, key=lambda x: x.priority, reverse=True)
        self.coordinator = next(agent for agent in agents if agent.role == "コーディネーター")
        self.current_topic = ""

    def process_query(self, query: str, max_iterations: int = CONFIG['max_iterations']):
        context = ""
        for iteration in range(max_iterations):
            logging.info(f"ラウンド {iteration + 1} 開始")
            print(f"\nラウンド {iteration + 1}:")

            coordinator_response = self.coordinator.respond(query, context)
            self.current_topic, next_speaker = self.parse_coordinator_response(coordinator_response)
            print(f"{self.coordinator.name}（コーディネーター）の指示:\n{coordinator_response}")

            if self.check_all_tasks_completed() and self.confirm_action("全てのエージェントがタスク完了を報告しました。議論を終了しますか？"):
                break

            context += f"\nラウンド {iteration + 1} - コーディネーター: {coordinator_response}"
            
            if next_speaker:
                agent = next((a for a in self.agents if a.name == next_speaker), None)
                if agent:
                    supplement = agent.respond(query, context, self.current_topic)
                    print(f"\n{agent.name}（{agent.role}）の回答:\n{supplement}")
                    context += f"\n{agent.name}: {supplement}"
            else:
                supplements = self.get_supplements(query, context)
                for agent, supplement in supplements:
                    print(f"\n{agent.name}（{agent.role}）からの補足:\n{supplement}")
                    context += f"\n{agent.name}: {supplement}"

            summary, next_question = self.generate_summary_and_question(context)
            print(f"\n議論のサマリー:\n{summary}")
            print(f"\n次のラウンドの質問:\n{next_question}")
            context += f"\n\nサマリー: {summary}\n次の質問: {next_question}"

            if not self.confirm_action("議論を続けますか？"):
                break

        print("\n最終的なまとめ:")
        final_summary = self.coordinator.respond(query, context + "\n\n上記を踏まえ、最終的または暫定的なまとめを提供してください。")
        print(final_summary)
        logging.info("議論のまとめ完了")
        for agent in self.agents:
            agent.task_completed = False

    def get_supplements(self, query: str, context: str) -> List[Tuple[Agent, str]]:
        return [(agent, agent.respond(query, context, self.current_topic)) 
                for agent in self.agents 
                if agent != self.coordinator and "補足は不要です" not in agent.respond(query, context, self.current_topic)]

    @staticmethod
    def parse_coordinator_response(response: str) -> Tuple[str, str]:
        topic = next((line.split("トピック:")[1].strip() for line in response.split('\n') if "トピック:" in line), "")
        next_speaker = next((line.split("次の発言者:")[1].strip() for line in response.split('\n') if "次の発言者:" in line), "")
        return topic, next_speaker

    def generate_summary_and_question(self, context: str) -> Tuple[str, str]:
        summary = self.coordinator.respond(f"{context}\n\n上記の議論を簡潔にまとめてください。", "")
        next_question = self.coordinator.respond(f"{context}\n{summary}\n\n次のラウンドで議論すべき重要な質問を1つ提案してください。", "")
        return summary, next_question

    def check_all_tasks_completed(self) -> bool:
        return all(agent.task_completed for agent in self.agents)

    @staticmethod
    def confirm_action(prompt: str) -> bool:
        return input(f"\n{prompt} (はい/いいえ): ").lower() == 'はい'

def main():
    agents = [Agent(**agent_config) for agent_config in CONFIG['agents']]
    team = AgentTeam(agents)

    def signal_handler(sig, frame):
        logging.info("プログラム中断")
        print('\nプログラムを中断します。')
        for agent in agents:
            agent.cleanup()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    logging.info("AIエージェントチャット開始")
    print("AIエージェントチームとのチャットを開始します。終了するには'exit'とだけ入力してください。")

    try:
        while True:
            query = input("\nあなたの質問: ")
            if query.lower() == 'exit':
                logging.info("ユーザーがプログラム終了")
                break
            team.process_query(query)
    except Exception as e:
        logging.error(f"予期せぬエラー: {str(e)}")
        print(f"予期せぬエラーが発生しました: {e}")
    finally:
        logging.info("プログラム終了")
        print('プログラムを終了します。')
        for agent in agents:
            agent.cleanup()

if __name__ == "__main__":
    main()
