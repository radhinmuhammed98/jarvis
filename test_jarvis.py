import sys
from core.intent_parser import IntentParser
from core.executor import CommandExecutor
from core.control_context import init_control_context
from core.device_memory import init_device_memory

init_control_context()
init_device_memory()

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
test("do whatever it takes to find the files")
test("exit")
test("make a horror lighting")
test("turn off lights in 5 seconds")
