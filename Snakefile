from snakemake.utils import validate

configfile: "configs/easy.yaml"

validate(config,schema="configs/schema.json")

container: "docker://ghcr.io/gekoramy/playground:1d9222ef3470906f13c9d1e6ee760647d9876068"


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
        seed=config["seed"],
        **config["wmpy_synthetic"],
    )


def wmibench_synthetic_structured() -> list[str]:
    if "wmibench_synthetic_structured" not in config:
        return []

    return expand(
        "wmibench_synthetic_structured/{name}_{size}_{seed}",
        seed=config["seed"],
        **config["wmibench_synthetic_structured"],
    )


def wmibench_synthetic_pa() -> list[str]:
    if "wmibench_synthetic_pa" not in config:
        return []

    return expand(
        "wmibench_synthetic_pa/r{reals}_b{bools}_d{depth}_s{seed}_{m}",
        m=[f"{n}" for n in range(1,6)],
        seed=config["seed"],
        **config["wmibench_synthetic_pa"],
    )


rule all:
    input:
        expand("assets/plots/{column}.vs.{suffix}",
            column=["time", "enumerating", "npolys", "nuniquepolys", "nuniquepolys to npolys", "survival"],
            suffix=["pdf", "png"]
        ),
        expand("assets/plots/{column}.only-exists.{suffix}",
            column=["models", "models to npolys", "models to nuniquepolys"],
            suffix=["pdf", "png"]
        ),
        expand("assets/plots/{column}.steps.{suffix}",
           column=["s", "max_rss"],
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
        script="src.plot"
    shell:
        """
        python -m {params.script} \
          --column {wildcards.column:q} \
          --type {wildcards.type} \
          --timeout_tlemmas {config[timeout][tlemmas]} \
          --timeout_compilator {config[timeout][compilator]} \
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
        tlemmas=[
            *["assets/tlemmas/{type}/{density}." + suffix for suffix in ["err", "steps"]],
            "assets/benchmarks/tlemmas/{type}/{density}.jsonl"
        ],
        tddnnf_d4=[
            *["assets/tddnnf/d4/{type}/{density}." + suffix for suffix in ["err"]],
            "assets/benchmarks/tddnnf/d4/{type}/{density}.jsonl"
        ],
        tddnnf_sdd=[
            *["assets/tddnnf/sdd/{type}/{density}." + suffix for suffix in ["err"]],
            "assets/benchmarks/tddnnf/sdd/{type}/{density}.jsonl"
        ],
        tddnnf_x_constrained_sdd=[
            *["assets/tddnnf/x_constrained_sdd/{type}/{density}." + suffix for suffix in["err"]],
            "assets/benchmarks/tddnnf/x_constrained_sdd/{type}/{density}.jsonl"
        ],
        tddnnf_A_constrained_sdd=[
            *["assets/tddnnf/A_constrained_sdd/{type}/{density}." + suffix for suffix in["err"]],
            "assets/benchmarks/tddnnf/A_constrained_sdd/{type}/{density}.jsonl"
        ],
        tddnnf_exists_x_d4=[
            *["assets/tddnnf_exists_x/d4/{type}/{density}." + suffix for suffix in ["err"]],
            "assets/benchmarks/tddnnf_exists_x/d4/{type}/{density}.jsonl"
        ],
        tddnnf_exists_x_sdd=[
            *["assets/tddnnf_exists_x/sdd/{type}/{density}." + suffix for suffix in ["err", "steps"]],
            "assets/benchmarks/tddnnf_exists_x/sdd/{type}/{density}.jsonl"
        ],
        tddnnf_exists_A_d4=[
            *["assets/tddnnf_exists_A/d4/{type}/{density}." + suffix for suffix in ["err"]],
            "assets/benchmarks/tddnnf_exists_A/d4/{type}/{density}.jsonl"
        ],
        tddnnf_exists_A_sdd=[
            *["assets/tddnnf_exists_A/sdd/{type}/{density}." + suffix for suffix in ["err", "steps"]],
            "assets/benchmarks/tddnnf_exists_A/sdd/{type}/{density}.jsonl"
        ],
        decdnnf_d4=[
            *["assets/decdnnf/tddnnf/d4/{type}/{density}." + suffix for suffix in ["err", "models"]],
            "assets/benchmarks/decdnnf/tddnnf/d4/{type}/{density}.jsonl"
        ],
        decdnnf_sdd=[
            *["assets/decdnnf/tddnnf/sdd/{type}/{density}." + suffix for suffix in ["err", "models"]],
            "assets/benchmarks/decdnnf/tddnnf/sdd/{type}/{density}.jsonl"
        ],
        decdnnf_x_constrained_sdd=[
            *["assets/decdnnf/tddnnf/x_constrained_sdd/{type}/{density}." + suffix for suffix in ["err", "models"]],
            "assets/benchmarks/decdnnf/tddnnf/x_constrained_sdd/{type}/{density}.jsonl"
        ],
        decdnnf_A_constrained_sdd=[
            *["assets/decdnnf/tddnnf/A_constrained_sdd/{type}/{density}." + suffix for suffix in ["err", "models"]],
            "assets/benchmarks/decdnnf/tddnnf/A_constrained_sdd/{type}/{density}.jsonl"
        ],
        decdnnf_exists_x_d4=[
            *["assets/decdnnf/tddnnf_exists_x/d4/{type}/{density}." + suffix for suffix in ["err", "models"]],
            "assets/benchmarks/decdnnf/tddnnf_exists_x/d4/{type}/{density}.jsonl"
        ],
        decdnnf_exists_x_sdd=[
            *["assets/decdnnf/tddnnf_exists_x/sdd/{type}/{density}." + suffix for suffix in ["err", "models"]],
            "assets/benchmarks/decdnnf/tddnnf_exists_x/sdd/{type}/{density}.jsonl"
        ],
        decdnnf_exists_A_d4=[
            *["assets/decdnnf/tddnnf_exists_A/d4/{type}/{density}." + suffix for suffix in ["err", "models"]],
            "assets/benchmarks/decdnnf/tddnnf_exists_A/d4/{type}/{density}.jsonl"
        ],
        decdnnf_exists_A_sdd=[
            *["assets/decdnnf/tddnnf_exists_A/sdd/{type}/{density}." + suffix for suffix in ["err", "models"]],
            "assets/benchmarks/decdnnf/tddnnf_exists_A/sdd/{type}/{density}.jsonl"
        ],
        sae=[
            *["assets/wmi/sae/noop/{type}/{density}." + suffix for suffix in ["out", "err", "steps"]],
            "assets/benchmarks/sae/noop/{type}/{density}.jsonl"
        ],
        decdnnf_baseline_d4=[
            *["assets/wmi/decdnnf_baseline/d4/noop/{type}/{density}." + suffix for suffix in ["out", "err", "steps"]],
            "assets/benchmarks/decdnnf_baseline/d4/noop/{type}/{density}.jsonl"
        ],
        decdnnf_baseline_sdd=[
            *["assets/wmi/decdnnf_baseline/sdd/noop/{type}/{density}." + suffix for suffix in ["out", "err", "steps"]],
            "assets/benchmarks/decdnnf_baseline/sdd/noop/{type}/{density}.jsonl"
        ],
        decdnnf_baseline_x_constrained_sdd=[
            *["assets/wmi/decdnnf_baseline/x_constrained_sdd/noop/{type}/{density}." + suffix for suffix in ["out", "err", "steps"]],
            "assets/benchmarks/decdnnf_baseline/x_constrained_sdd/noop/{type}/{density}.jsonl"
        ],
        decdnnf_baseline_A_constrained_sdd=[
            *["assets/wmi/decdnnf_baseline/A_constrained_sdd/noop/{type}/{density}." + suffix for suffix in ["out", "err", "steps"]],
            "assets/benchmarks/decdnnf_baseline/A_constrained_sdd/noop/{type}/{density}.jsonl"
        ],
        decdnnf_two_steps_exists_x_d4=[
            *["assets/wmi/decdnnf_two_steps/exists_x/d4/noop/{type}/{density}." + suffix for suffix in ["out", "err", "steps"]],
            "assets/benchmarks/decdnnf_two_steps/exists_x/d4/noop/{type}/{density}.jsonl"
        ],
        decdnnf_two_steps_exists_x_sdd=[
            *["assets/wmi/decdnnf_two_steps/exists_x/sdd/noop/{type}/{density}." + suffix for suffix in ["out", "err", "steps"]],
            "assets/benchmarks/decdnnf_two_steps/exists_x/sdd/noop/{type}/{density}.jsonl"
        ],
        decdnnf_two_steps_exists_A_d4=[
            *["assets/wmi/decdnnf_two_steps/exists_A/d4/noop/{type}/{density}." + suffix for suffix in ["out", "err", "steps"]],
            "assets/benchmarks/decdnnf_two_steps/exists_A/d4/noop/{type}/{density}.jsonl"
        ],
        decdnnf_two_steps_exists_A_sdd=[
            *["assets/wmi/decdnnf_two_steps/exists_A/sdd/noop/{type}/{density}." + suffix for suffix in ["out", "err", "steps"]],
            "assets/benchmarks/decdnnf_two_steps/exists_A/sdd/noop/{type}/{density}.jsonl"
        ]
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
    container: "docker://ghcr.io/gekoramy/wmibench:438e69f7d4b7192034617b9aedf9c774e6e606d2"
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
            r"assets/densities/wmibench_synthetic_pa/r{reals,\d+}_b{bools,\d+}_d{depth,\d+}_s{seed,\d+}_" f"{n}" ".json"
            for n in range(1,6)
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
          --models 5 \
          --output $tmp_dir

        mv $tmp_dir/*/* assets/densities/wmibench_synthetic_pa

        rm -rf $tmp_dir
        """


rule compute_tlemmas:
    threads: 13
    resources:
        mem="20GB"
    input:
        "assets/densities/{type}/{density}.json"
    output:
        tlemmas="assets/tlemmas/{type}/{density}.smt2",
        mapping="assets/tlemmas/{type}/{density}.mapping",
        phi_n_tlemmas="assets/tlemmas/{type}/{density}.phi_n_tlemmas.smt2"
    log:
        steps="assets/tlemmas/{type}/{density}.steps",
        err="assets/tlemmas/{type}/{density}.err"
    params:
        script="src.tddnnf.tlemmas"
    benchmark:
        "assets/benchmarks/tlemmas/{type}/{density}.jsonl"
    shell:
        """
        timeout --verbose {config[timeout][tlemmas]}m \
          python -m {params.script} \
          --density {input} \
          --tlemmas {output.tlemmas} \
          --mapping {output.mapping} \
          --phi_n_tlemmas {output.phi_n_tlemmas} \
          --steps {log.steps} \
          --cores {threads} \
          2> {log.err} \
          || touch {output}
        """


rule smtlib_to_bcs12:
    threads: 1
    input:
        phi_n_tlemmas="assets/tlemmas/{type}/{density}.phi_n_tlemmas.smt2",
        mapping="assets/tlemmas/{type}/{density}.mapping",
    output:
        bcs12="assets/tddnnf/d4/{type}/{density}.bc"
    params:
        script="src.tddnnf.smtlib_to_bcs12"
    shell:
        """
        if [[ -s {input.phi_n_tlemmas:q} ]]; then
          python -m {params.script} \
            --smtlib {input.phi_n_tlemmas} \
            --mapping {input.mapping} \
            --bcs12 {output.bcs12}
        fi

        touch {output}
        """


rule bcs12_projected:
    threads: 1
    input:
        bcs12="assets/tddnnf/d4/{type}/{density}.bc",
        mapping="assets/tlemmas/{type}/{density}.mapping"
    output:
        bcs12="assets/tddnnf_exists_{qo,[xA]}/d4/{type}/{density}.bc"
    params:
        script="src.tddnnf.exists"
    shell:
        """
        if [[ -s {input.bcs12:q} ]]; then
          python -m {params.script} \
            --steps /dev/null \
            --mapping {input.mapping} \
            --quantify_out {wildcards.qo} \
            bcs12 \
            --bcs12 {input.bcs12} \
            --projected_bcs12 {output.bcs12}
        fi

        touch {output}
        """


rule compile_tddnnf_with_d4:
    threads: 1
    resources:
        mem="20GB"
    input:
        bcs12="assets/{tddnnf}/d4/{type}/{density}.bc"
    output:
        nnf="assets/{tddnnf}/d4/{type}/{density}.to-fix-nnf"
    log:
        err="assets/{tddnnf}/d4/{type}/{density}.err"
    benchmark:
        "assets/benchmarks/{tddnnf}/d4/{type}/{density}.jsonl"
    shell:
        """
        if [[ -s {input.bcs12:q} ]]; then
          timeout --verbose {config[timeout][compilator]}m \
            d4 \
            --input {input.bcs12} \
            --input-type circuit \
            --remove-gates 1 \
            --dump-file {output.nnf} \
            &> {log.err} \
            || touch {output}
        fi

        touch {output}
        """


rule fix_nnf:
    threads: 1
    input:
        "assets/{nnf}.to-fix-nnf"
    output:
        "assets/{nnf}.nnf"
    params:
        "src.tddnnf.fix_nnf"
    shell:
        """
        python -m {params} --nnf {input} {output}
        """


rule compile_tddnnf_with_sdd:
    threads: 1
    resources:
        mem="20GB"
    input:
        phi_n_tlemmas="assets/tlemmas/{type}/{density}.phi_n_tlemmas.smt2",
        mapping="assets/tlemmas/{type}/{density}.mapping",
    output:
        sdd="assets/tddnnf/sdd/{type}/{density}.sdd",
        vtree="assets/tddnnf/sdd/{type}/{density}.vtree"
    log:
        err="assets/tddnnf/sdd/{type}/{density}.err"
    benchmark:
        "assets/benchmarks/tddnnf/sdd/{type}/{density}.jsonl"
    params:
        script="src.tddnnf.smtlib_to_sdd"
    shell:
        """
        if [[ -s {input.phi_n_tlemmas:q} ]]; then
          timeout --verbose {config[timeout][compilator]}m \
            python -m {params.script} \
            --smtlib {input.phi_n_tlemmas} \
            --mapping {input.mapping} \
            --sdd {output.sdd} \
            --vtree {output.vtree} \
            2> {log.err} \
            || touch {output}
        fi

        touch {output}
        """


rule compile_tddnnf_with_constrained_sdd:
    threads: 1
    resources:
        mem="20GB"
    input:
        phi_n_tlemmas="assets/tlemmas/{type}/{density}.phi_n_tlemmas.smt2",
        mapping="assets/tlemmas/{type}/{density}.mapping",
    output:
        sdd="assets/tddnnf/{on,[xA]}_constrained_sdd/{type}/{density}.min-sdd",
        vtree="assets/tddnnf/{on,[xA]}_constrained_sdd/{type}/{density}.min-vtree"
    log:
        err="assets/tddnnf/{on,[xA]}_constrained_sdd/{type}/{density}.err"
    benchmark:
        "assets/benchmarks/tddnnf/{on,[xA]}_constrained_sdd/{type}/{density}.jsonl"
    params:
        script="src.tddnnf.smtlib_to_sdd"
    shell:
        """
        if [[ -s {input.phi_n_tlemmas:q} ]]; then
          timeout --verbose {config[timeout][compilator]}m \
            python -m {params.script} \
            --smtlib {input.phi_n_tlemmas} \
            --mapping {input.mapping} \
            --sdd {output.sdd} \
            --vtree {output.vtree} \
            --constrained {wildcards.on} \
            2> {log.err} \
            || touch {output}
        fi

        touch {output}
        """


rule compile_tddnnf_projected_with_sdd:
    threads: 1
    resources:
        mem="20GB"
    input:
        mapping="assets/tlemmas/{type}/{density}.mapping",
        sdd="assets/tddnnf/sdd/{type}/{density}.min-sdd",
        vtree="assets/tddnnf/sdd/{type}/{density}.min-vtree"
    output:
        sdd="assets/tddnnf_exists_{qo,[xA]}/sdd/{type}/{density}.sdd",
        vtree="assets/tddnnf_exists_{qo,[xA]}/sdd/{type}/{density}.vtree"
    log:
        steps="assets/tddnnf_exists_{qo,[xA]}/sdd/{type}/{density}.steps",
        err="assets/tddnnf_exists_{qo,[xA]}/sdd/{type}/{density}.err"
    benchmark:
        "assets/benchmarks/tddnnf_exists_{qo,[xA]}/sdd/{type}/{density}.jsonl"
    params:
        script="src.tddnnf.exists"
    shell:
        """
        if [[ -s {input.sdd:q} ]]; then
          timeout --verbose {config[timeout][compilator]}m \
            python -m {params.script} \
            --steps {log.steps} \
            --mapping {input.mapping} \
            --quantify_out {wildcards.qo} \
            sdd \
            --vtree {input.vtree} \
            --sdd {input.sdd} \
            --projected_vtree {output.vtree} \
            --projected_sdd {output.sdd} \
            2> {log.err} \
            || touch {output}
        fi

        touch {output}
        """


rule minimize_nnf:
    threads: 1
    input:
        nnf="assets/{nnf}.nnf",
    output:
        nnf="assets/{nnf}.min-nnf",
    benchmark:
        "assets/benchmarks/minimize_nnf/{nnf}.jsonl"
    params:
        script="src.minimize_nnf"
    shell:
        """
        if [[ -s {input.nnf:q} ]]; then
          python -m {params.script} \
            --nnf {input.nnf} {output.nnf}
        fi

        touch {output}
        """


rule minimize_sdd:
    threads: 1
    input:
        vtree="assets/{sdd}.vtree",
        sdd="assets/{sdd}.sdd"
    output:
        vtree="assets/{sdd}.min-vtree",
        sdd="assets/{sdd}.min-sdd"
    benchmark:
        "assets/benchmarks/minimize_sdd/{sdd}.jsonl"
    params:
        script="src.minimize_sdd"
    shell:
        """
        if [[ -s {input.sdd:q} ]]; then
          python -m {params.script} \
            --vtree {input.vtree} {output.vtree} \
            --sdd {input.sdd} {output.sdd} \
            --minutes {config[timeout][minimize]}
        fi
        
        touch {output}
        """


rule sdd_to_nnf:
    threads: 1
    input:
        "{sdd}.min-sdd"
    output:
        "{sdd}.nnf"
    params:
        script="src.sdd_to_nnf"
    shell:
        """
        python -m {params.script} \
          --sdd {input} \
          --nnf {output}
        """


rule decdnnf:
    threads: 13
    input:
        "assets/{nnf}.min-nnf"
    output:
        "assets/decdnnf/{nnf}.models"
    log:
        "assets/decdnnf/{nnf}.err"
    benchmark:
        "assets/benchmarks/decdnnf/{nnf}.jsonl"
    shell:
        """
        if [[ -s {input:q} ]]; then
          timeout --verbose {config[timeout][enumerator]}m \
            decdnnf_rs model-enumeration \
            --compact-free-vars \
            --input {input} \
            --threads {threads} \
            1> {output} \
            2> {log} \
            || touch {output}
        fi
        
        touch {output}
        """


rule compute_wmi_with_sae:
    threads: 13
    resources:
        mem="20GB"
    input:
        "assets/densities/{type}/{density}.json"
    output:
        wmi="assets/wmi/sae/{int,noop|latte}/{type}/{density}.out",
    log:
        steps="assets/wmi/sae/{int,noop|latte}/{type}/{density}.steps",
        err="assets/wmi/sae/{int,noop|latte}/{type}/{density}.err"
    benchmark:
        "assets/benchmarks/sae/{int,noop|latte}/{type}/{density}.jsonl"
    params:
        script="src.wmi"
    shell:
        """
        timeout --verbose {config[timeout][enumerator]}m \
          python -m {params.script} \
          --density {input} \
          --integrator {wildcards.int} \
          --parallel \
          --cached \
          --steps {log.steps} \
          --cores {threads} \
          sae \
          1> {output.wmi} \
          2> {log.err} \
          || touch {output}
        """


rule compute_wmi_with_decdnnf_baseline:
    threads:
        lambda wildcards: 1 if wildcards.int == "noop" else 13
    resources:
        mem=lambda wildcards: None if wildcards.int == "noop" else "20GB"
    input:
        density="assets/densities/{type}/{density}.json",
        models="assets/decdnnf/tddnnf/{compiler}/{type}/{density}.models",
        mapping="assets/tlemmas/{type}/{density}.mapping"
    output:
        wmi="assets/wmi/decdnnf_baseline/{compiler,d4|.*sdd}/{int,noop|latte}/{type}/{density}.out"
    log:
        steps="assets/wmi/decdnnf_baseline/{compiler,d4|.*sdd}/{int,noop|latte}/{type}/{density}.steps",
        err="assets/wmi/decdnnf_baseline/{compiler,d4|.*sdd}/{int,noop|latte}/{type}/{density}.err"
    benchmark:
        "assets/benchmarks/decdnnf_baseline/{compiler,d4|.*sdd}/{int,noop|latte}/{type}/{density}.jsonl"
    params:
        script="src.wmi"
    shell:
        """
        if [[ -s {input.models:q} ]]; then
          timeout --verbose {config[timeout][enumerator]}m \
            python -m {params.script} \
            --density {input.density} \
            --integrator {wildcards.int} \
            --parallel \
            --cached \
            --steps {log.steps} \
            --cores {threads} \
            decdnnf_baseline \
            --models {input.models} \
            --mapping {input.mapping} \
            1> {output.wmi} \
            2> {log.err} \
            || touch {output}
        fi

        touch {output}
        """


rule compute_wmi_with_decdnnf_two_steps_sdd:
    threads: 26
    resources:
        mem="20GB"
    input:
        density="assets/densities/{type}/{density}.json",
        models_projected="assets/decdnnf/tddnnf_exists_{qo}/sdd/{type}/{density}.models",
        mapping="assets/tlemmas/{type}/{density}.mapping",
        vtree="assets/tddnnf/sdd/{type}/{density}.min-vtree",
        sdd="assets/tddnnf/sdd/{type}/{density}.min-sdd"
    output:
        wmi="assets/wmi/decdnnf_two_steps/exists_{qo}/sdd/{int,noop|latte}/{type}/{density}.out"
    log:
        steps="assets/wmi/decdnnf_two_steps/exists_{qo}/sdd/{int,noop|latte}/{type}/{density}.steps",
        err="assets/wmi/decdnnf_two_steps/exists_{qo}/sdd/{int,noop|latte}/{type}/{density}.err"
    benchmark:
        "assets/benchmarks/decdnnf_two_steps/exists_{qo}/sdd/{int,noop|latte}/{type}/{density}.jsonl"
    params:
        script="src.wmi"
    shell:
        """
        if [[ -s {input.models_projected:q} ]]; then
          timeout --verbose {config[timeout][enumerator]}m \
            python -m {params.script} \
            --density {input.density} \
            --integrator {wildcards.int} \
            --parallel \
            --cached \
            --steps {log.steps} \
            --cores {threads} \
            decdnnf_two_steps \
            --models_projected {input.models_projected} \
            --mapping {input.mapping} \
            sdd \
            --vtree {input.vtree} \
            --sdd {input.sdd} \
            1> {output.wmi} \
            2> {log.err} \
            || touch {output}
        fi

        touch {output}
        """


rule compute_wmi_with_decdnnf_two_steps_d4:
    threads: 26
    resources:
        mem="20GB"
    input:
        density="assets/densities/{type}/{density}.json",
        models_projected="assets/decdnnf/tddnnf_exists_{qo}/d4/{type}/{density}.models",
        mapping="assets/tlemmas/{type}/{density}.mapping",
        nnf="assets/tddnnf/d4/{type}/{density}.min-nnf",
    output:
        wmi="assets/wmi/decdnnf_two_steps/exists_{qo}/d4/{int,noop|latte}/{type}/{density}.out"
    log:
        steps="assets/wmi/decdnnf_two_steps/exists_{qo}/d4/{int,noop|latte}/{type}/{density}.steps",
        err="assets/wmi/decdnnf_two_steps/exists_{qo}/d4/{int,noop|latte}/{type}/{density}.err"
    benchmark:
        "assets/benchmarks/decdnnf_two_steps/exists_{qo}/d4/{int,noop|latte}/{type}/{density}.jsonl"
    params:
        script="src.wmi"
    shell:
        """
        if [[ -s {input.models_projected:q} ]]; then
          timeout --verbose {config[timeout][enumerator]}m \
            python -m {params.script} \
            --density {input.density} \
            --integrator {wildcards.int} \
            --parallel \
            --cached \
            --steps {log.steps} \
            --cores {threads} \
            decdnnf_two_steps \
            --models_projected {input.models_projected} \
            --mapping {input.mapping} \
            d4 \
            --nnf {input.nnf} \
            1> {output.wmi} \
            2> {log.err} \
            || touch {output}
        fi

        touch {output}
        """
