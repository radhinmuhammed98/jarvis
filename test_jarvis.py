import sys
from core.intent_parser import IntentParser
from core.executor import CommandExecutor

parser = IntentParser()
executor = CommandExecutor()

def test(text):
    intent = parser.parse(text)
    resp = executor.execute(intent)
    print(f"'{text}' -> {intent['action']} -> {resp}")

test("open chrome")
test("search python flask tutorial")
test("what time is it")
test("system info")
test("turn on light")
test("hello")
test("exit")
