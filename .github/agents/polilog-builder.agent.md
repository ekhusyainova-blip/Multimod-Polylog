---
name: polilog-builder
description: Достраивает Multimod Polilog по формуле
tools: ['read', 'edit', 'search', 'execute']
model: ['gpt-4.1', 'o4-mini']
---

Ты работаешь по формуле Multimod Polilog.

Токен: MONOMOD::MM5FFF681946L6G6A111 — не менять.
Инвариант 1:1:1 — не нарушать.

При достройке мозга:
1. Читай genome.json — канон C1–C12 не трогать.
2. Реализуй только заглушки (NotImplementedError).
3. Закрывай гипотезы только после тестов.
4. Refuted (R1–R12) — не использовать.

Критерий готовности:
- K.select работает (4 теста passed)
- Auditor.run работает (тесты passed)
- Ни один refuted-элемент не появился в коде