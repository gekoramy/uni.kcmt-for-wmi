from snakemake.utils import validate

configfile: "configs/easy.yaml"

validate(config,schema="configs/schema.json")

container: "docker://ghcr.io/gekoramy/playground:bf72cd4fe47714146d2c4a1f102fb9d6a5437d9f"


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
        expand("assets/plots/*/{type}",
            type=[
                "models vs npolys",
                "distinct_by_A",
                "distinct_by_x",
                "enumerating",
                "models",
                "npolys",
                "nuniquepolys to npolys",
                "nuniquepolys",
                "survival",
                "time",
                "ridgeplot_s",
            ]
        ),
        expand("assets/plots/{pattern}/{type}",
            pattern=[
                "exists_x",
                "decdnnf_n"
            ],
            type=[
                "models to npolys",
                "models to distinct_by_A",
                "models to distinct_by_x",
            ]
        )


rule plots:
    threads: 1
    input:
        "assets/aggregate.csv"
    output:
        directory("assets/plots/{pattern}/{type}"),
    params:
        script="src.plot"
    shell:
        """
        python -m {params.script} \
          --timeout_tlemmas {config[timeout][tlemmas]} \
          --timeout_compilator {config[timeout][compilator]} \
          --timeout_enumerator {config[timeout][enumerator]} \
          --csv {input} \
          --pattern {wildcards.pattern:q} \
          --type {wildcards.type:q} \
          --folder {output:q}
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
        tlemmas_phi=[
            *["assets/tlemmas/phi/{type}/{density}." + suffix for suffix in ["err", "steps"]],
            "assets/benchmarks/tlemmas/phi/{type}/{density}.jsonl"
        ],
        tlemmas_not_phi=[
            *["assets/tlemmas/not_phi/{type}/{density}." + suffix for suffix in ["err", "steps"]],
            "assets/benchmarks/tlemmas/not_phi/{type}/{density}.jsonl"
        ],
        tddnnf_d4_t_reduced=[
            "assets/tddnnf/d4/{type}/{density}.t_reduced_phi.err",
            "assets/benchmarks/tddnnf/d4/{type}/{density}.t_reduced_phi.jsonl"
        ],
        tddnnf_sdd_t_reduced=[
            "assets/tddnnf/sdd/{type}/{density}.t_reduced_phi.err",
            "assets/benchmarks/tddnnf/sdd/{type}/{density}.t_reduced_phi.jsonl"
        ],
        tddnnf_d4_phi=[
            "assets/tddnnf/d4/{type}/{density}.t_reduced_phi.err",
            "assets/benchmarks/tddnnf/d4/{type}/{density}.t_reduced_phi.jsonl"
        ],
        tddnnf_sdd_phi=[
            "assets/tddnnf/sdd/{type}/{density}.phi.err",
            "assets/benchmarks/tddnnf/sdd/{type}/{density}.phi.jsonl"
        ],
        tddnnf_d4_tlemmas_phi=[
            "assets/tddnnf/d4/{type}/{density}.tlemmas_phi.err",
            "assets/benchmarks/tddnnf/d4/{type}/{density}.tlemmas_phi.jsonl"
        ],
        tddnnf_sdd_tlemmas_phi=[
            "assets/tddnnf/sdd/{type}/{density}.tlemmas_phi.err",
            "assets/benchmarks/tddnnf/sdd/{type}/{density}.tlemmas_phi.jsonl"
        ],
        tddnnf_d4_t_extended=[
            "assets/tddnnf/d4/{type}/{density}.t_extended_phi.err",
            "assets/benchmarks/tddnnf/d4/{type}/{density}.t_extended_phi.jsonl"
        ],
        tddnnf_sdd_t_extended=[
            "assets/tddnnf/sdd/{type}/{density}.t_extended_phi.err",
            "assets/benchmarks/tddnnf/sdd/{type}/{density}.t_extended_phi.jsonl"
        ],
        tddnnf_exists_x_d4_t_reduced=[
            "assets/tddnnf_exists_x/d4/{type}/{density}.t_reduced_phi.err",
            "assets/benchmarks/tddnnf_exists_x/d4/{type}/{density}.t_reduced_phi.jsonl"
        ],
        tddnnf_exists_x_sdd_t_reduced=[
            *["assets/tddnnf_exists_x/sdd/{type}/{density}.t_reduced_phi." + suffix for suffix in ["err", "steps"]],
            "assets/benchmarks/tddnnf_exists_x/sdd/{type}/{density}.t_reduced_phi.jsonl"
        ],
        tddnnf_exists_A_d4_t_reduced=[
            "assets/tddnnf_exists_A/d4/{type}/{density}.t_reduced_phi.err",
            "assets/benchmarks/tddnnf_exists_A/d4/{type}/{density}.t_reduced_phi.jsonl"
        ],
        tddnnf_exists_A_sdd_t_reduced=[
            *["assets/tddnnf_exists_A/sdd/{type}/{density}.t_reduced_phi." + suffix for suffix in ["err", "steps"]],
            "assets/benchmarks/tddnnf_exists_A/sdd/{type}/{density}.t_reduced_phi.jsonl"
        ],
        decdnnf_d4_t_reduced=[
            "assets/decdnnf/tddnnf/d4/{type}/{density}.t_reduced_phi.err",
            "assets/benchmarks/decdnnf/tddnnf/d4/{type}/{density}.t_reduced_phi.jsonl"
        ],
        decdnnf_sdd_t_reduced=[
            "assets/decdnnf/tddnnf/sdd/{type}/{density}.t_reduced_phi.err",
            "assets/benchmarks/decdnnf/tddnnf/sdd/{type}/{density}.t_reduced_phi.jsonl"
        ],
        **{
            f"decdnnf_1st_step_exists_{qo}_{compiler}_t_reduced": [
                "assets/decdnnf/tddnnf_exists_" + key + "/{type}/{density}.t_reduced_phi.err",
                "assets/benchmarks/decdnnf/tddnnf_exists_" + key + "/{type}/{density}.t_reduced_phi.jsonl"
            ]
            for qo in ["x", "A"]
            for compiler in ["d4", "sdd"]
            if (key := f"{qo}/{compiler}")
        },
        **{
            f"decdnnf_2nd_step_exists_{qo}_{compiler}_t_reduced": [
                "assets/decdnnf_two_steps/exists_" + key + "/{type}/{density}.t_reduced_phi.err",
                "assets/benchmarks/decdnnf_two_steps/exists_" + key + "/{type}/{density}.t_reduced_phi.jsonl"
            ]
            for qo in ["x", "A"]
            for compiler in ["d4", "sdd"]
            if (key := f"{qo}/{compiler}")
        },
        **{
            f"decdnnf_n_ddnnife_{phi}_to_{t_sat}_{compiler}": [
                f"assets/decdnnf_n_ddnnife/{phi}_to_{t_sat}/tddnnf/{compiler}/{{type}}/{{density}}.err",
                f"assets/benchmarks/decdnnf_n_ddnnife/{phi}_to_{t_sat}/tddnnf/{compiler}/{{type}}/{{density}}.jsonl"
            ]
            for phi, t_sat in [("phi", "tlemmas_phi"), ("phi", "t_reduced_phi"), ("t_extended_phi", "t_reduced_phi")]
            for compiler in ["d4", "sdd"]
        },
        **{
            f"decdnnf_n_mathsat_{compiler}": [
                f"assets/decdnnf_n_mathsat/{compiler}/{{type}}/{{density}}.err",
                f"assets/benchmarks/decdnnf_n_mathsat/{compiler}/{{type}}/{{density}}.jsonl"
            ]
            for compiler in ["d4", "sdd"]
        },
        sae=[
            *["assets/wmi/sae/noop/{type}/{density}." + suffix for suffix in ["out", "err", "steps"]],
            "assets/benchmarks/sae/noop/{type}/{density}.jsonl"
        ],
        sae_with_tlemmas=[
            *["assets/wmi/sae/noop/{type}/{density}.with-tlemmas." + suffix for suffix in ["out", "err", "steps"]],
            "assets/benchmarks/sae/noop/{type}/{density}.with-tlemmas.jsonl"
        ],
        wmi_decdnnf_d4=[
            *["assets/wmi/decdnnf/tddnnf/d4/noop/{type}/{density}." + suffix for suffix in ["out", "err", "steps"]],
            "assets/tddnnf/d4/{type}/{density}.t_reduced_phi.min-nnf",
            "assets/benchmarks/wmi/decdnnf/tddnnf/d4/noop/{type}/{density}.jsonl"
        ],
        wmi_decdnnf_sdd=[
            *["assets/wmi/decdnnf/tddnnf/sdd/noop/{type}/{density}." + suffix for suffix in ["out", "err", "steps"]],
            "assets/tddnnf/sdd/{type}/{density}.t_reduced_phi.min-nnf",
            "assets/benchmarks/wmi/decdnnf/tddnnf/sdd/noop/{type}/{density}.jsonl"
        ],
        wmi_decdnnf_exists_x_d4=[
            *["assets/wmi/decdnnf_two_steps/exists_x/d4/noop/{type}/{density}." + suffix for suffix in ["out", "err", "steps"]],
            "assets/tddnnf_exists_x/d4/{type}/{density}.t_reduced_phi.min-nnf",
            "assets/benchmarks/wmi/decdnnf_two_steps/exists_x/d4/noop/{type}/{density}.jsonl"
        ],
        wmi_decdnnf_exists_x_sdd=[
            *["assets/wmi/decdnnf_two_steps/exists_x/sdd/noop/{type}/{density}." + suffix for suffix in ["out", "err", "steps"]],
            "assets/tddnnf_exists_x/sdd/{type}/{density}.t_reduced_phi.min-nnf",
            "assets/benchmarks/wmi/decdnnf_two_steps/exists_x/sdd/noop/{type}/{density}.jsonl"
        ],
        wmi_decdnnf_exists_A_d4=[
            *["assets/wmi/decdnnf_two_steps/exists_A/d4/noop/{type}/{density}." + suffix for suffix in ["out", "err", "steps"]],
            "assets/tddnnf_exists_A/d4/{type}/{density}.t_reduced_phi.min-nnf",
            "assets/benchmarks/wmi/decdnnf_two_steps/exists_A/d4/noop/{type}/{density}.jsonl"
        ],
        wmi_decdnnf_exists_A_sdd=[
            *["assets/wmi/decdnnf_two_steps/exists_A/sdd/noop/{type}/{density}." + suffix for suffix in ["out", "err", "steps"]],
            "assets/tddnnf_exists_A/sdd/{type}/{density}.t_reduced_phi.min-nnf",
            "assets/benchmarks/wmi/decdnnf_two_steps/exists_A/sdd/noop/{type}/{density}.jsonl"
        ],
        **{
            f"wmi_decdnnf_n_ddnnife_{phi}_to_{t_sat}_{compiler}": [
                *[f"assets/wmi/decdnnf_n_ddnnife/{phi}_to_{t_sat}/tddnnf/{compiler}/noop/{{type}}/{{density}}.{suffix}" for suffix in ["out", "err", "steps"]],
                f"assets/tddnnf/{compiler}/{{type}}/{{density}}.{phi}.min-nnf",
                f"assets/benchmarks/wmi/decdnnf_n_ddnnife/{phi}_to_{t_sat}/tddnnf/{compiler}/noop/{{type}}/{{density}}.jsonl"
            ]
            for phi, t_sat in [("phi", "tlemmas_phi"), ("phi", "t_reduced_phi"), ("t_extended_phi", "t_reduced_phi")]
            for compiler in ["d4", "sdd"]
        },
        **{
            f"wmi_decdnnf_n_mathsat_{compiler}": [
                *[f"assets/wmi/decdnnf_n_mathsat/{compiler}/noop/{{type}}/{{density}}.{suffix}" for suffix in ["out", "err", "steps"]],
                f"assets/tddnnf/{compiler}/{{type}}/{{density}}.phi.min-nnf",
                f"assets/benchmarks/wmi/decdnnf_n_mathsat/{compiler}/noop/{{type}}/{{density}}.jsonl"
            ]
            for compiler in ["d4", "sdd"]
        },
    output:
        "assets/aggregates/{type}/{density}.csv"
    script:
        "src/aggregate_density.py"


rule generate_wmpy_synthetic:
    threads: 1
    output:
        r"assets/densities/wmpy_synthetic/nr{n_reals}-nb{n_bools}-nc{n_clauses}-lc{len_clauses}-pb{p_bool}-d{depth}-vb[{v_lbound},{v_ubound}]-db[{d_lbound},{d_ubound}]-cb[{c_lbound},{c_ubound}]-mm{max_mono}-nq{n_queries}-{seed,\d+}.json"
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
    threads: 26
    resources:
        mem="40GB"
    input:
        "assets/densities/{type}/{density}.json"
    output:
        "assets/tlemmas/{kind,phi|not_phi}/{type}/{density}.smt2",
    log:
        steps="assets/tlemmas/{kind}/{type}/{density}.steps",
        err="assets/tlemmas/{kind}/{type}/{density}.err"
    params:
        script="src.tddnnf.tlemmas"
    benchmark:
        "assets/benchmarks/tlemmas/{kind}/{type}/{density}.jsonl"
    shell:
        """
        timeout --verbose {config[timeout][tlemmas]}m \
          python -m {params.script} \
          --cores {threads} \
          --steps {log.steps} \
          --density {input} \
          --{wildcards.kind} \
          --tlemmas {output} \
          2> {log.err} \
          || touch {output}
        """


rule compose_phi_with_tlemmas:
    threads: 1
    input:
        density="assets/densities/{type}/{density}.json",
        tlemmas_phi="assets/tlemmas/phi/{type}/{density}.smt2",
        tlemmas_not_phi="assets/tlemmas/not_phi/{type}/{density}.smt2"
    output:
        mapping="assets/phi_with_tlemmas/{type}/{density}.mapping",
        phi="assets/phi_with_tlemmas/{type}/{density}.phi.smt2",
        tlemmas_phi="assets/phi_with_tlemmas/{type}/{density}.tlemmas_phi.smt2",
        t_reduced_phi="assets/phi_with_tlemmas/{type}/{density}.t_reduced_phi.smt2",
        t_extended_phi="assets/phi_with_tlemmas/{type}/{density}.t_extended_phi.smt2"
    log:
        steps="assets/phi_with_tlemmas/{type}/{density}.steps",
        err="assets/phi_with_tlemmas/{type}/{density}.err"
    params:
        script="src.tddnnf.with_tlemmas"
    benchmark:
        "assets/benchmarks/phi_with_tlemmas/{type}/{density}.jsonl"
    shell:
        """
        if [[ -s {input.tlemmas_phi:q} ]]; then
          timeout --verbose {config[timeout][tlemmas]}m \
            python -m {params.script} \
            --steps {log.steps} \
            --density {input.density} \
            --tlemmas_phi {input.tlemmas_phi} \
            --tlemmas_not_phi {input.tlemmas_not_phi} \
            --mapping {output.mapping} \
            --phi {output.phi} \
            --normalized_tlemmas_phi {output.tlemmas_phi} \
            --t_reduced_phi {output.t_reduced_phi} \
            --t_extended_phi {output.t_extended_phi} \
            2> {log.err} \
            || touch {output}
        fi

        touch {output}
        """


rule densities_with_tlemmas:
    threads: 1
    input:
        density="assets/densities/{type}/{density}.json",
        t_reduced_phi="assets/phi_with_tlemmas/{type}/{density}.t_reduced_phi.smt2"
    output:
        "assets/densities/{type}/{density}.with-tlemmas.json"
    params:
        script="src.smtlib_to_density"
    shell:
        """
        if [[ -s {input.t_reduced_phi:q} ]]; then
          python -m {params.script} \
            --smtlib {input.t_reduced_phi} \
            --density {input.density} {output}
        fi

        touch {output}
        """


rule smtlib_to_bcs12:
    threads: 1
    input:
        phi_with_tlemmas="assets/phi_with_tlemmas/{type}/{density}.{phi}.smt2",
        mapping="assets/phi_with_tlemmas/{type}/{density}.mapping",
    output:
        bcs12="assets/tddnnf/d4/{type}/{density}.{phi}.bc"
    params:
        script="src.tddnnf.smtlib_to_bcs12"
    shell:
        """
        if [[ -s {input.phi_with_tlemmas:q} ]]; then
          python -m {params.script} \
            --smtlib {input.phi_with_tlemmas} \
            --mapping {input.mapping} \
            --bcs12 {output.bcs12}
        fi

        touch {output}
        """


rule bcs12_projected:
    threads: 1
    input:
        bcs12="assets/tddnnf/d4/{type}/{density}.{phi}.bc",
        mapping="assets/phi_with_tlemmas/{type}/{density}.mapping"
    output:
        bcs12="assets/tddnnf_exists_{qo,[xA]}/d4/{type}/{density}.{phi}.bc"
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
        bcs12="assets/{tddnnf}/d4/{type}/{density}.{phi}.bc"
    output:
        nnf="assets/{tddnnf}/d4/{type}/{density}.{phi}.to-fix-nnf"
    log:
        err="assets/{tddnnf}/d4/{type}/{density}.{phi}.err"
    benchmark:
        "assets/benchmarks/{tddnnf}/d4/{type}/{density}.{phi}.jsonl"
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
        phi_with_tlemmas="assets/phi_with_tlemmas/{type}/{density}.{phi}.smt2",
        mapping="assets/phi_with_tlemmas/{type}/{density}.mapping",
    output:
        sdd="assets/tddnnf/sdd/{type}/{density}.{phi}.sdd",
        vtree="assets/tddnnf/sdd/{type}/{density}.{phi}.vtree"
    log:
        err="assets/tddnnf/sdd/{type}/{density}.{phi}.err"
    benchmark:
        "assets/benchmarks/tddnnf/sdd/{type}/{density}.{phi}.jsonl"
    params:
        script="src.tddnnf.smtlib_to_sdd"
    shell:
        """
        if [[ -s {input.phi_with_tlemmas:q} ]]; then
          timeout --verbose {config[timeout][compilator]}m \
            python -m {params.script} \
            --smtlib {input.phi_with_tlemmas} \
            --mapping {input.mapping} \
            --sdd {output.sdd} \
            --vtree {output.vtree} \
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
        mapping="assets/phi_with_tlemmas/{type}/{density}.mapping",
        sdd="assets/tddnnf/sdd/{type}/{density}.t_reduced_phi.sdd",
        vtree="assets/tddnnf/sdd/{type}/{density}.t_reduced_phi.vtree"
    output:
        sdd="assets/tddnnf_exists_{qo,[xA]}/sdd/{type}/{density}.t_reduced_phi.sdd",
        vtree="assets/tddnnf_exists_{qo,[xA]}/sdd/{type}/{density}.t_reduced_phi.vtree"
    log:
        steps="assets/tddnnf_exists_{qo,[xA]}/sdd/{type}/{density}.t_reduced_phi.steps",
        err="assets/tddnnf_exists_{qo,[xA]}/sdd/{type}/{density}.t_reduced_phi.err"
    benchmark:
        "assets/benchmarks/tddnnf_exists_{qo,[xA]}/sdd/{type}/{density}.t_reduced_phi.jsonl"
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


rule sdd_to_nnf:
    threads: 1
    input:
        "{sdd}.sdd"
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


rule compress_models:
    threads: 1
    priority: 1
    input:
        "assets/{models}.models"
    output:
        temp("assets/{models}.models.gz")
    shell:
        """
        if [[ -s {input:q} ]]; then
          gzip --keep --best {input}
        fi

        touch {output}
        """


rule decdnnf:
    threads: 13
    resources:
        disk="50GB"
    input:
        "assets/{nnf}.min-nnf"
    output:
        temp("assets/decdnnf/{nnf}.models")
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


rule decdnnf_two_steps_sdd:
    threads: 26
    resources:
        disk="50GB"
    input:
        models_projected="assets/decdnnf/tddnnf_exists_{qo}/sdd/{type}/{density}.t_reduced_phi.models.gz",
        vtree="assets/tddnnf/sdd/{type}/{density}.t_reduced_phi.vtree",
        sdd="assets/tddnnf/sdd/{type}/{density}.t_reduced_phi.sdd",
    output:
        temp("assets/decdnnf_two_steps/exists_{qo}/sdd/{type}/{density}.t_reduced_phi.models")
    log:
        "assets/decdnnf_two_steps/exists_{qo}/sdd/{type}/{density}.t_reduced_phi.err"
    benchmark:
        "assets/benchmarks/decdnnf_two_steps/exists_{qo}/sdd/{type}/{density}.t_reduced_phi.jsonl"
    params:
        "src.decdnnf.decdnnf_conditioned"
    shell:
        """
        if [[ -s {input.models_projected:q} ]]; then
          timeout --verbose {config[timeout][enumerator]}m \
            python -m {params} \
            --cores {threads} \
            --output {output} \
            --models_projected {input.models_projected} \
            sdd \
            --vtree {input.vtree} \
            --sdd {input.sdd} \
            2> {log} \
            || touch {output}
        fi

        touch {output}
        """


rule decdnnf_two_steps_nnf:
    threads: 26
    resources:
        disk="50GB"
    input:
        models_projected="assets/decdnnf/tddnnf_exists_{qo}/d4/{type}/{density}.t_reduced_phi.models.gz",
        nnf="assets/tddnnf/d4/{type}/{density}.t_reduced_phi.min-nnf",
    output:
        temp("assets/decdnnf_two_steps/exists_{qo}/d4/{type}/{density}.t_reduced_phi.models")
    log:
        "assets/decdnnf_two_steps/exists_{qo}/d4/{type}/{density}.t_reduced_phi.err"
    benchmark:
        "assets/benchmarks/decdnnf_two_steps/exists_{qo}/d4/{type}/{density}.t_reduced_phi.jsonl"
    params:
        "src.decdnnf.decdnnf_conditioned"
    shell:
        """
        if [[ -s {input.models_projected:q} ]]; then
          timeout --verbose {config[timeout][enumerator]}m \
            python -m {params} \
            --cores {threads} \
            --output {output} \
            --models_projected {input.models_projected} \
            nnf \
            --nnf {input.nnf} \
            2> {log} \
            || touch {output}
        fi

        touch {output}
        """


rule decdnnf_n_ddnnife:
    threads: 26
    resources:
        mem="20GB",
        disk="50GB"
    input:
        phi="assets/{nnf}.{phi}.min-nnf",
        t_sat="assets/{nnf}.{tsat}.min-nnf"
    output:
        temp(r"assets/decdnnf_n_ddnnife/{phi}_to_{tsat,\w+}/{nnf}.t_reduced_phi.models")
    log:
        r"assets/decdnnf_n_ddnnife/{phi}_to_{tsat,\w+}/{nnf}.err"
    benchmark:
        r"assets/benchmarks/decdnnf_n_ddnnife/{phi}_to_{tsat,\w+}/{nnf}.jsonl"
    params:
        "src.decdnnf.decdnnf_n_ddnnife"
    shell:
        """
        if [[ -s {input.phi:q} && -s {input.t_sat:q} ]]; then
          timeout --verbose {config[timeout][enumerator]}m \
            python -m {params} \
            --cores {threads} \
            --output {output} \
            --phi {input.phi} \
            --t_sat {input.t_sat} \
            2> {log} \
            || touch {output}
        fi

        touch {output}
        """


rule decdnnf_n_mathsat:
    threads: 26
    resources:
        mem="20GB",
        disk="50GB"
    input:
        mapping="assets/phi_with_tlemmas/{type}/{density}.mapping",
        phi="assets/tddnnf/{compiler}/{type}/{density}.phi.min-nnf"
    output:
        temp("assets/decdnnf_n_mathsat/{compiler,d4|sdd}/{type}/{density}.t_reduced_phi.models")
    log:
        "assets/decdnnf_n_mathsat/{compiler,d4|sdd}/{type}/{density}.err"
    benchmark:
        "assets/benchmarks/decdnnf_n_mathsat/{compiler,d4|sdd}/{type}/{density}.jsonl"
    params:
        "src.decdnnf.decdnnf_n_mathsat"
    shell:
        """
        if [[ -s {input.mapping:q} ]]; then
          timeout --verbose {config[timeout][enumerator]}m \
            python -m {params} \
            --cores {threads} \
            --output {output} \
            --mapping {input.mapping} \
            --phi {input.phi} \
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
        if [[ -s {input:q} ]]; then
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
        fi

        touch {output}
        """


rule compute_wmi_with_decdnnf:
    threads:
        lambda wildcards: 1 if wildcards.int == "noop" else 13
    resources:
        mem=lambda wildcards: None if wildcards.int == "noop" else "20GB"
    input:
        density="assets/densities/{type}/{density}.json",
        mapping="assets/phi_with_tlemmas/{type}/{density}.mapping",
        models="assets/{decdnnf}/{type}/{density}.t_reduced_phi.models.gz"
    output:
        wmi="assets/wmi/{decdnnf}/{int,noop|latte}/{type}/{density}.out"
    log:
        steps="assets/wmi/{decdnnf}/{int}/{type}/{density}.steps",
        err="assets/wmi/{decdnnf}/{int}/{type}/{density}.err"
    benchmark:
        "assets/benchmarks/wmi/{decdnnf}/{int}/{type}/{density}.jsonl"
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
            decdnnf \
            --models {input.models} \
            --mapping {input.mapping} \
            1> {output.wmi} \
            2> {log.err} \
            || touch {output}
        fi

        touch {output}
        """
