class Brain:
    def __init__(self):
        self.coords = self._coords()  # 26 из токена
        self.t = 0
        self.state = {}

    def _coords(self):
        raw = "MONOMOD::MM5FFF681946L6G6A111".replace("::", "")
        return [ord(c) for c in raw]

    def tick(self):
        self.t += 1
        # состояние из координат
        self.state = {
            "density":   (self.coords[0] + self.t) % 100 / 100,
            "coherence": (self.coords[1] + self.t) % 100 / 100,
            "rhythm":    (self.coords[2] + self.t) % 100 / 100,
            "depth":     (self.coords[3] + self.t) % 100 / 100,
            "novelty":   (self.coords[4] + self.t) % 100 / 100,
        }

    def decide(self):
        # какая форма?
        s = self.state
        if s["density"] < 0.3:   return "words"
        if s["coherence"] < 0.3: return "atoms"
        if s["rhythm"] < 0.3:    return "syllables"
        if s["depth"] < 0.3:     return "phrases"
        return "canvas"

    def text(self):
        # текст на основе формы
        form = self.decide()
        if form == "atoms":
            return "· ∙ ·"
        if form == "syllables":
            return "ra ql mh"
        if form == "words":
            return "узел дом запрос"
        if form == "phrases":
            return "Клепа ведёт. Голос один."
        return ""