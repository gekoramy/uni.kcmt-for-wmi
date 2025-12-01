from theorydd.tdd.theory_bdd import TheoryBDD
from pysmt.shortcuts import And, Implies, Or, Iff, LT, LE, Real, Symbol, REAL, Plus


def main():
    # BUILD YOUR T-FORMULA FROM THE PYSMT LIBRARY

    x = Symbol("x", REAL)
    y = Symbol("y", REAL)
    z = Symbol("z", REAL)

    phi = And(
        Implies(
            LT(x, y),
            LE(Plus(x, z), Real(0)),
        ),
        Or(LE(Real(-10), z), LT(y, z)),
        Iff(
            LT(x, y),
            LT(z, y),
        ),
    )

    logger = {}

    # BUILD YOUR DD WITH THE CONSTRUCTOR
    bdd = TheoryBDD(
        phi,
        solver="partial",  # used to compute all-SMT and extract lemmas
        computation_logger=logger,
    )

    # USE YOUR DD

    # MODEL COUNTING
    print("Models: ", bdd.count_models())

    # SIZE
    print("Size in nodes: ", bdd.count_nodes())

    # DUMP YOUR DD ON A SVG FILE
    bdd.graphic_dump("theory_bdd_example.svg")

    # CHECK YOUR LOGGER
    print(logger)


if __name__ == "__main__":
    main()
