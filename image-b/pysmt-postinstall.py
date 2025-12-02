import pysmt.shortcuts as S
from pysmt.typing import INT

hello = [S.Symbol(s, INT) for s in "hello"]
world = [S.Symbol(s, INT) for s in "world"]
letters = set(hello + world)
formula = S.And(
    [
        *[
            condition
            for letter in letters
            for condition in (S.GE(letter, S.Int(1)), S.LE(letter, S.Int(9)))
        ],
        S.AllDifferent(letters),
        S.Equals(S.Plus(hello), S.Plus(world)),
    ]
)

print("Serialization of the formula:")
print(formula)

model = S.get_model(formula)
print(model)
