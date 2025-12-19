from snakemake.utils import validate

configfile: "configs/easy.json"

validate(config, schema="configs/schema.json")

rule all:
    input:
        expand(
            "assets/wmi/{enum}/{int}/{type}/{density}.txt",
            enum=config["enum"],
            int=config["int"],
            type=config["type"],
            density=expand(
                "nr{n_reals}-nb{n_bools}-nc{n_clauses}-lc{len_clauses}-pb{p_bool}-d{depth}-vb[{v_lbound},{v_ubound}]-db[{d_lbound},{d_ubound}]-cb[{c_lbound},{c_ubound}]-mm{max_mono}-nq{n_queries}-{seed}",
                **config["density"],
            ),
        )

rule generate_synthetic_wmpy:
    output:
        "assets/densities/synthetic-wmpy/nr{n_reals}-nb{n_bools}-nc{n_clauses}-lc{len_clauses}-pb{p_bool}-d{depth}-vb[{v_lbound},{v_ubound}]-db[{d_lbound},{d_ubound}]-cb[{c_lbound},{c_ubound}]-mm{max_mono}-nq{n_queries}-{seed}.json"
    params:
        script="wmpy/benchmarks/synthetic.py"
    shell:
        """
        python {params.script} \
          {wildcards.seed} \
          --directory assets/densities/synthetic-wmpy \
          --n_reals {wildcards.n_reals} \
          --n_bools {wildcards.n_bools} \
          --n_clauses {wildcards.n_clauses} \
          --len_clauses {wildcards.len_clauses} \
          --n_queries {wildcards.n_queries} \
          --p_bool {wildcards.p_bool} \
          --depth {wildcards.depth} \
          --vbounds {wildcards.v_lbound} {wildcards.v_ubound} \
          --dbounds {wildcards.d_lbound} {wildcards.d_ubound} \
          --cbounds {wildcards.c_lbound} {wildcards.c_ubound} \
          --max_monomials {wildcards.max_mono}
        """

rule compute_tlemmas:
    input:
        "assets/densities/{type}/{density}.json"
    output:
        tlemmas="assets/tlemmas/{type}/{density}.smt2",
        steps="assets/tlemmas/{type}/{density}.ndjson"
    params:
        script="src.tlemmas"
    shell:
        """
        timeout 20m python -m {params.script} \
          --density {input} \
          --tlemmas {output.tlemmas} \
          --steps {output.steps}
        """

rule compute_wmi_with_sae:
    input:
        "assets/densities/{type}/{density}.json"
    output:
        wmi="assets/wmi/sae/{int,(noop)|(latte)}/{type}/{density}.txt",
        steps="assets/wmi/sae/{int,(noop)|(latte)}/{type}/{density}.ndjson"
    params:
        script="src.wmi"
    shell:
        """
        timeout 10m python -m {params.script} \
          --density {input} \
          --enumerator sae \
          --integrator {wildcards.int} \
          --steps {output.steps} \
          > {output.wmi}
        """

rule compute_wmi_with_decdnnf:
    input:
        density="assets/densities/{type}/{density}.json",
        tlemmas="assets/tlemmas/{type}/{density}.smt2"
    output:
        wmi="assets/wmi/{enum,(d4)|(sdd)}/{int,(noop)|(latte)}/{type}/{density}.txt",
        steps="assets/wmi/{enum,(d4)|(sdd)}/{int,(noop)|(latte)}/{type}/{density}.ndjson"
    params:
        script="src.wmi"
    shell:
        """
        timeout 10m python -m {params.script} \
          --density {input.density} \
          --enumerator {wildcards.enum} \
          --integrator {wildcards.int} \
          --tlemmas {input.tlemmas} \
          --steps {output.steps} \
          > {output.wmi}
        """
