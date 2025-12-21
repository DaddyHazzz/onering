class FakeDelta:
    def __init__(self, content: str):
        self.content = content

class FakeChoice:
    def __init__(self, content: str):
        self.delta = FakeDelta(content)

class FakeChunk:
    def __init__(self, content: str):
        self.choices = [FakeChoice(content)]

class FakeCompletions:
    def create(self, *args, **kwargs):
        for token in ["Hello ", "World", "!\n"]:
            yield FakeChunk(token)

class FakeChat:
    def __init__(self):
        self.completions = FakeCompletions()

class FakeGroq:
    def __init__(self, api_key: str = ""):
        self.chat = FakeChat()

class FakeResponse:
    def __init__(self, content: str):
        self.content = content

class FakeLLM:
    def invoke(self, messages):
        numbered = (
            "1/6 First tweet with number\n\n"
            "Tweet 2: Second tweet label\n\n"
            "(3) Third tweet parentheses\n\n"
            "[4] Fourth tweet bracket\n\n"
            "5. Fifth tweet dot\n\n"
            "- Sixth tweet bullet"
        )
        return FakeResponse(numbered)
