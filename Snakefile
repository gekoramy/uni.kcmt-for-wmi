from snakemake.utils import validate

configfile: "configs/easy.yaml"

validate(config,schema="configs/schema.json")

container: "docker://ghcr.io/gekoramy/playground:latest"


def densities() -> list[str]:
    return [
        *wmpy_synthetic(),
        *wmibench_synthetic_structured(),
        *wmibench_synthetic_pa(),
    ]


def wmpy_synthetic() -> list[str]:
    if "wmpy_synthetic" not in config:
        return []

    return expand(
        "wmpy_synthetic/nr{n_reals}-nb{n_bools}-nc{n_clauses}-lc{len_clauses}-pb{p_bool}-d{depth}-vb[{v_lbound},{v_ubound}]-db[{d_lbound},{d_ubound}]-cb[{c_lbound},{c_ubound}]-mm{max_mono}-nq{n_queries}-{seed}",
        **config["wmpy_synthetic"],
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
        expand("assets/plots/{column}.time.{suffix}",
            column=["enumerating", "enumerating full"],
            suffix=["pdf", "png"]
        ),
        expand("assets/plots/npolys.int.{suffix}",
            suffix=["pdf", "png"]
        )


rule plot:
    threads: 1
    input:
        "assets/aggregate.csv"
    output:
        "assets/plots/{column}.{type}.pdf",
        "assets/plots/{column}.{type}.png"
    params:
        script="src/plot.py"
    shell:
        """
        python {params.script} \
          --column {wildcards.column:q} \
          --type {wildcards.type} \
          --timeout_tlemmas {config[timeout][tlemmas]} \
          --timeout_enumerator {config[timeout][enumerator]} \
          --csv {input} \
          --output {output:q}
        """


rule aggregate:
    threads: 13
    input:
        expand("assets/aggregates/{density}.csv",
            density=densities()
        )
    output:
        "assets/aggregate.csv"
    script:
        "src/aggregate.py"


rule aggregate_density:
    threads: 1
    input:
        tlemmas=["assets/tlemmas/{type}/{density}." + suffix for suffix in ["err", "steps"]],
        tddnnf_d4=["assets/tddnnf/d4/{type}/{density}." + suffix for suffix in ["err", "steps"]],
        tddnnf_sdd=["assets/tddnnf/sdd/{type}/{density}." + suffix for suffix in ["err", "steps"]],
        sae=["assets/wmi/sae/noop/{type}/{density}." + suffix for suffix in ["out", "err", "steps"]],
        decdnnf_baseline_d4=["assets/wmi/decdnnf_baseline/d4/noop/{type}/{density}." + suffix for suffix in ["out", "err", "steps"]],
        decdnnf_baseline_sdd=["assets/wmi/decdnnf_baseline/sdd/noop/{type}/{density}." + suffix for suffix in ["out", "err", "steps"]]
    output:
        "assets/aggregates/{type}/{density}.csv"
    script:
        "src/aggregate_density.py"


rule generate_wmpy_synthetic:
    threads: 1
    output:
        "assets/densities/wmpy_synthetic/nr{n_reals}-nb{n_bools}-nc{n_clauses}-lc{len_clauses}-pb{p_bool}-d{depth}-vb[{v_lbound},{v_ubound}]-db[{d_lbound},{d_ubound}]-cb[{c_lbound},{c_ubound}]-mm{max_mono}-nq{n_queries}-{seed}.json"
    params:
        script="src/synthetic.py"
    shell:
        """
        python {params.script} \
          {wildcards.seed} \
          --directory assets/densities/wmpy_synthetic \
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
    threads: 13
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
        timeout --verbose {config[timeout][tlemmas]}m \
          python -m {params.script} \
          --density {input} \
          --tlemmas {output.tlemmas} \
          --steps {output.steps} \
          --cores {threads} \
          2> {output.timeout} \
          || [ $? -eq 124 ]
        
        touch {output}
        """


rule compile_tddnnf_with_d4:
    threads: 1
    input:
        density="assets/densities/{type}/{density}.json",
        tlemmas="assets/tlemmas/{type}/{density}.smt2"
    output:
        steps="assets/tddnnf/d4/{type}/{density}.steps",
        timeout="assets/tddnnf/d4/{type}/{density}.err",
        mapping="assets/tddnnf/d4/{type}/{density}.json",
        nnf="assets/tddnnf/d4/{type}/{density}.nnf"
    params:
        script="src.tddnnf"
    shell:
        """
        timeout --verbose {config[timeout][compilator]}m \
          python -m {params.script} \
          --cores {threads} \
          --density {input.density} \
          --tlemmas {input.tlemmas} \
          --steps {output.steps} \
          --mapping {output.mapping} \
          d4 \
          --nnf {output.nnf} \
          2> {output.timeout} \
          || [ $? -eq 124 ]

        touch {output}
        """


rule compile_tddnnf_with_sdd:
    threads: 1
    input:
        density="assets/densities/{type}/{density}.json",
        tlemmas="assets/tlemmas/{type}/{density}.smt2"
    output:
        steps="assets/tddnnf/sdd/{type}/{density}.steps",
        timeout="assets/tddnnf/sdd/{type}/{density}.err",
        mapping="assets/tddnnf/sdd/{type}/{density}.json",
        sdd="assets/tddnnf/sdd/{type}/{density}.sdd",
        vtree="assets/tddnnf/sdd/{type}/{density}.vtree"
    params:
        script="src.tddnnf"
    shell:
        """
        timeout --verbose {config[timeout][compilator]}m \
          python -m {params.script} \
          --cores {threads} \
          --density {input.density} \
          --tlemmas {input.tlemmas} \
          --steps {output.steps} \
          --mapping {output.mapping} \
          sdd \
          --sdd {output.sdd} \
          --vtree {output.vtree} \
          2> {output.timeout} \
          || [ $? -eq 124 ]

        touch {output}
        """


rule sdd_to_nnf:
    threads: 1
    input:
        "{sdd}.sdd"
    output:
        "{sdd}.nnf"
    params:
        script="src.sdd2nnf"
    shell:
        """
        python -m {params.script} \
          --sdd {input} \
          --nnf {output}
        """


rule compute_wmi_with_sae:
    threads: 13
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
        timeout --verbose {config[timeout][enumerator]}m \
          python -m {params.script} \
          --density {input} \
          --integrator {wildcards.int} \
          --steps {output.steps} \
          --cores {threads} \
          sae \
          1> {output.wmi} \
          2> {output.timeout} \
          || [ $? -eq 124 ]
        
        touch {output}
        """


rule compute_wmi_with_decdnnf_baseline:
    threads: 13
    input:
        density="assets/densities/{type}/{density}.json",
        nnf="assets/tddnnf/{compiler}/{type}/{density}.nnf",
        mapping="assets/tddnnf/{compiler}/{type}/{density}.json"
    output:
        wmi="assets/wmi/decdnnf_baseline/{compiler,d4|sdd}/{int,noop|latte}/{type}/{density}.out",
        steps="assets/wmi/decdnnf_baseline/{compiler,d4|sdd}/{int,noop|latte}/{type}/{density}.steps",
        timeout="assets/wmi/decdnnf_baseline/{compiler,d4|sdd}/{int,noop|latte}/{type}/{density}.err"
    params:
        script="src.wmi"
    shell:
        """
        if [[ -s {input.nnf:q} ]]; then
          timeout --verbose {config[timeout][enumerator]}m \
            python -m {params.script} \
            --density {input.density} \
            --integrator {wildcards.int} \
            --steps {output.steps} \
            --cores {threads} \
            decdnnf_baseline \
            --nnf {input.nnf} \
            --mapping {input.mapping} \
            1> {output.wmi} \
            2> {output.timeout} \
            || [ $? -eq 124 ]
        fi
          
        touch {output}
        """
