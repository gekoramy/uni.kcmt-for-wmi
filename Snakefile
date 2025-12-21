from snakemake.utils import validate

configfile: "configs/easy.yaml"

validate(config, schema="configs/schema.json")

container: "docker://ghcr.io/gekoramy/playground:latest"


def densities() -> list[str]:
    return [
        *synthetic_wmpy(),
        *wmibench_synthetic_structured(),
        *wmibench_synthetic_pa(),
    ]


def synthetic_wmpy() -> list[str]:
    if "synthetic_wmpy" not in config:
        return []

    return expand(
        "synthetic_wmpy/nr{n_reals}-nb{n_bools}-nc{n_clauses}-lc{len_clauses}-pb{p_bool}-d{depth}-vb[{v_lbound},{v_ubound}]-db[{d_lbound},{d_ubound}]-cb[{c_lbound},{c_ubound}]-mm{max_mono}-nq{n_queries}-{seed}",
        **config["synthetic_wmpy"],
    )


def wmibench_synthetic_structured() -> list[str]:
    if "wmibench_synthetic_structured" not in config:
        return []

    return expand(
        "wmibench_synthetic_structured/{name}_{size}_{seed}",
        **config["wmibench_synthetic_structured"],
    )


def wmibench_synthetic_pa() -> list[str]:
    if "wmibench_synthetic_pa" not in config:
        return []

    return expand(
        "wmibench_synthetic_pa/r{reals}_b{bools}_d{depth}_s{seed}_{m}",
        m=[f"{n:02}" for n in range(1,21)],
        **config["wmibench_synthetic_pa"],
    )


rule all:
    input:
        expand("assets/plots/{column}.{suffix}",
            column=["enumerating", "npolys", "enumerating full", "parsing density"],
            suffix=["pdf", "png"]
        )


rule plot:
    threads: 1
    input:
        "assets/aggregate.csv"
    output:
        "assets/plots/{column}.pdf",
        "assets/plots/{column}.png",
    params:
        script="src/plot.py"
    shell:
        """
        python {params.script} \
          --column {wildcards.column:q} \
          --csv {input} \
          --output {output:q}
        """


rule aggregate:
    threads: 1
    input:
        expand("assets/wmi/{enum}/noop/{density}.{suffix}",
            enum=["sae", "d4", "sdd"],
            density=densities(),
            suffix=["steps", "out", "err"],
        ),
        expand("assets/tlemmas/{density}.{suffix}",
            density=densities(),
            suffix=["steps", "err"],
        )
    output:
        "assets/aggregate.csv"
    script:
        "src/aggregate.py"


rule generate_synthetic_wmpy:
    threads: 1
    output:
        "assets/densities/synthetic_wmpy/nr{n_reals}-nb{n_bools}-nc{n_clauses}-lc{len_clauses}-pb{p_bool}-d{depth}-vb[{v_lbound},{v_ubound}]-db[{d_lbound},{d_ubound}]-cb[{c_lbound},{c_ubound}]-mm{max_mono}-nq{n_queries}-{seed}.json"
    params:
        script="src/synthetic.py"
    shell:
        """
        python {params.script} \
          {wildcards.seed} \
          --directory assets/densities/synthetic_wmpy \
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


rule generate_wmibench_synthetic_structured:
    container: "docker://ghcr.io/gekoramy/wmibench:latest"
    threads: 1
    output:
        r"assets/densities/wmibench_synthetic_structured/{name,and_overlap|dual_paths|dual_paths_distinct|tpg_3ary_tree|tpg_path|tpg_star|uni}_{size,\d+}_{seed,\d+}.json"
    shell:
        """
        folder=$(python -c "from distutils.sysconfig import get_python_lib; print(get_python_lib())")
        
        python $folder/wmibench/synthetic/synthetic_structured.py \
          {wildcards.name} \
          {wildcards.size} \
          --seed {wildcards.seed} \
          --output_folder assets/densities/wmibench_synthetic_structured
        """


rule generate_wmibench_synthetic_pa:
    container: "docker://ghcr.io/gekoramy/wmibench:latest"
    threads: 1
    output:
        *[
            r"assets/densities/wmibench_synthetic_pa/r{reals,\d+}_b{bools,\d+}_d{depth,\d+}_s{seed,\d+}_" f"{n:02}" ".json"
            for n in range(1,21)
        ]
    shell:
        """
        folder=$(python -c "from distutils.sysconfig import get_python_lib; print(get_python_lib())")
        
        tmp_dir=$(mktemp -d -t wmibench-XXXXXXXXXX)

        python $folder/wmibench/synthetic/synthetic_pa.py \
          --reals {wildcards.reals} \
          --booleans {wildcards.bools} \
          --depth {wildcards.depth} \
          --seed {wildcards.seed} \
          --output $tmp_dir
          
        mv $tmp_dir/*/* assets/densities/wmibench_synthetic_pa
        
        rm -rf $tmp_dir
        """


rule compute_tlemmas:
    threads: 17
    input:
        "assets/densities/{type}/{density}.json"
    output:
        tlemmas="assets/tlemmas/{type}/{density}.smt2",
        steps="assets/tlemmas/{type}/{density}.steps",
        timeout="assets/tlemmas/{type}/{density}.err"
    params:
        script="src.tlemmas"
    shell:
        """
        timeout --verbose 20m \
          python -m {params.script} \
          --density {input} \
          --tlemmas {output.tlemmas} \
          --steps {output.steps} \
          --cores {threads} \
          2> {output.timeout} \
          || [ $? -eq 124 ]
        
        touch {output.tlemmas}
        touch {output.steps}
        """

rule compute_wmi_with_sae:
    threads: 17
    input:
        "assets/densities/{type}/{density}.json"
    output:
        wmi="assets/wmi/sae/{int,noop|latte}/{type}/{density}.out",
        steps="assets/wmi/sae/{int,noop|latte}/{type}/{density}.steps",
        timeout="assets/wmi/sae/{int,noop|latte}/{type}/{density}.err"
    params:
        script="src.wmi"
    shell:
        """
        timeout --verbose 10m \
          python -m {params.script} \
          --density {input} \
          --enumerator sae \
          --integrator {wildcards.int} \
          --steps {output.steps} \
          --cores {threads} \
          1> {output.wmi} \
          2> {output.timeout} \
          || [ $? -eq 124 ]
        
        touch {output.wmi}
        touch {output.steps}
        touch {output.timeout}
        """

rule compute_wmi_with_decdnnf:
    threads: 17
    input:
        density="assets/densities/{type}/{density}.json",
        tlemmas="assets/tlemmas/{type}/{density}.smt2"
    output:
        wmi="assets/wmi/{enum,d4|sdd}/{int,noop|latte}/{type}/{density}.out",
        steps="assets/wmi/{enum,d4|sdd}/{int,noop|latte}/{type}/{density}.steps",
        timeout="assets/wmi/{enum,d4|sdd}/{int,noop|latte}/{type}/{density}.err"
    params:
        script="src.wmi"
    shell:
        """
        if [[ -s "{input.tlemmas}" ]]; then
          timeout --verbose 10m \
            python -m {params.script} \
            --density {input.density} \
            --enumerator {wildcards.enum} \
            --integrator {wildcards.int} \
            --tlemmas {input.tlemmas} \
            --steps {output.steps} \
            --cores {threads} \
            1> {output.wmi} \
            2> {output.timeout} \
            || [ $? -eq 124 ]
        fi
          
        touch {output.wmi}
        touch {output.steps}
        touch {output.timeout}
        """
