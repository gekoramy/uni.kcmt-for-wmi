from snakemake.utils import validate

configfile: "configs/easy.yaml"

validate(config,schema="configs/schema.json")

container: "docker://ghcr.io/gekoramy/playground:814a8cfdba266a742d0626ff5f5bb15c7de596af"


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
            column=["time", "enumerating", "npolys", "nuniquepolys", "nuniquepolys to npolys", "survival",
                    "inspection-x", "inspection-A", "distinct_by_x", "distinct_by_A"],
            suffix=["pdf", "png"]
        ),
        expand("assets/plots/{column}.only-exists.{suffix}",
            column=["models", "models to npolys", "models to nuniquepolys", "models to distinct_by_x",
                    "models to distinct_by_A"],
            suffix=["pdf", "png"]
        ),
        expand("assets/plots/{column}.steps.{suffix}",
            column=["s", "max_rss"],
            suffix=["pdf", "png"]
        )


rule plot:
    threads: 1
    resources:
        mem="20GB"
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
        tlemmas_phi=[
            *["assets/tlemmas/phi/{type}/{density}." + suffix for suffix in ["err", "steps"]],
            "assets/benchmarks/tlemmas/phi/{type}/{density}.jsonl"
        ],
        tlemmas_not_phi=[
            *["assets/tlemmas/not_phi/{type}/{density}." + suffix for suffix in ["err", "steps"]],
            "assets/benchmarks/tlemmas/not_phi/{type}/{density}.jsonl"
        ],
        tddnnf_d4_t_reduced=[
            *["assets/tddnnf/d4/{type}/{density}.t_reduced_phi." + suffix for suffix in ["err"]],
            "assets/benchmarks/tddnnf/d4/{type}/{density}.t_reduced_phi.jsonl"
        ],
        tddnnf_sdd_t_reduced=[
            *["assets/tddnnf/sdd/{type}/{density}.t_reduced_phi." + suffix for suffix in ["err"]],
            "assets/benchmarks/tddnnf/sdd/{type}/{density}.t_reduced_phi.jsonl"
        ],
        tddnnf_d4_phi=[
            *["assets/tddnnf/d4/{type}/{density}.t_reduced_phi." + suffix for suffix in ["err"]],
            "assets/benchmarks/tddnnf/d4/{type}/{density}.t_reduced_phi.jsonl"
        ],
        tddnnf_sdd_phi=[
            *["assets/tddnnf/sdd/{type}/{density}.phi." + suffix for suffix in ["err"]],
            "assets/benchmarks/tddnnf/sdd/{type}/{density}.phi.jsonl"
        ],
        tddnnf_d4_t_extended=[
            *["assets/tddnnf/d4/{type}/{density}.t_extended_phi." + suffix for suffix in ["err"]],
            "assets/benchmarks/tddnnf/d4/{type}/{density}.t_extended_phi.jsonl"
        ],
        tddnnf_sdd_t_extended=[
            *["assets/tddnnf/sdd/{type}/{density}.t_extended_phi." + suffix for suffix in ["err"]],
            "assets/benchmarks/tddnnf/sdd/{type}/{density}.t_extended_phi.jsonl"
        ],
        tddnnf_exists_x_d4_t_reduced=[
            *["assets/tddnnf_exists_x/d4/{type}/{density}.t_reduced_phi." + suffix for suffix in ["err"]],
            "assets/benchmarks/tddnnf_exists_x/d4/{type}/{density}.t_reduced_phi.jsonl"
        ],
        tddnnf_exists_x_sdd_t_reduced=[
            *["assets/tddnnf_exists_x/sdd/{type}/{density}.t_reduced_phi." + suffix for suffix in ["err", "steps"]],
            "assets/benchmarks/tddnnf_exists_x/sdd/{type}/{density}.t_reduced_phi.jsonl"
        ],
        tddnnf_exists_A_d4_t_reduced=[
            *["assets/tddnnf_exists_A/d4/{type}/{density}.t_reduced_phi." + suffix for suffix in ["err"]],
            "assets/benchmarks/tddnnf_exists_A/d4/{type}/{density}.t_reduced_phi.jsonl"
        ],
        tddnnf_exists_A_sdd_t_reduced=[
            *["assets/tddnnf_exists_A/sdd/{type}/{density}.t_reduced_phi." + suffix for suffix in ["err", "steps"]],
            "assets/benchmarks/tddnnf_exists_A/sdd/{type}/{density}.t_reduced_phi.jsonl"
        ],
        decdnnf_d4_t_reduced=[
            *["assets/decdnnf/tddnnf/d4/{type}/{density}.t_reduced_phi." + suffix for suffix in ["err", "models.gz"]],
            "assets/benchmarks/decdnnf/tddnnf/d4/{type}/{density}.t_reduced_phi.jsonl"
        ],
        decdnnf_sdd_t_reduced=[
            *["assets/decdnnf/tddnnf/sdd/{type}/{density}.t_reduced_phi." + suffix for suffix in ["err", "models.gz"]],
            "assets/benchmarks/decdnnf/tddnnf/sdd/{type}/{density}.t_reduced_phi.jsonl"
        ],
        **{
            f"decdnnf_1st_step_exists_{qo}_{compiler}_t_reduced": [
                "assets/decdnnf/tddnnf_exists_" + key + "/{type}/{density}.t_reduced_phi.err",
                "assets/decdnnf/tddnnf_exists_" + key + "/{type}/{density}.t_reduced_phi.models.gz",
                "assets/benchmarks/decdnnf/tddnnf_exists_" + key + "/{type}/{density}.t_reduced_phi.jsonl"
            ]
            for qo in ["x", "A"]
            for compiler in ["d4", "sdd"]
            if (key := f"{qo}/{compiler}")
        },
        **{
            f"decdnnf_2nd_step_exists_{qo}_{compiler}_t_reduced": [
                "assets/decdnnf_two_steps/exists_" + key + "/{type}/{density}.t_reduced_phi.err",
                "assets/decdnnf_two_steps/exists_" + key + "/{type}/{density}.t_reduced_phi.models.gz",
                "assets/benchmarks/decdnnf_two_steps/exists_" + key + "/{type}/{density}.t_reduced_phi.jsonl"
            ]
            for qo in ["x", "A"]
            for compiler in ["d4", "sdd"]
            if (key := f"{qo}/{compiler}")
        },
        decdnnf_phi_n_reduce_d4=[
            "assets/decdnnf_phi_n_reduce/tddnnf/d4/{type}/{density}.t_reduced_phi.models.gz",
            "assets/decdnnf_phi_n_reduce/tddnnf/d4/{type}/{density}.err",
            "assets/benchmarks/decdnnf_phi_n_reduce/tddnnf/d4/{type}/{density}.jsonl"
        ],
        decdnnf_phi_n_reduce_sdd=[
            "assets/decdnnf_phi_n_reduce/tddnnf/sdd/{type}/{density}.t_reduced_phi.models.gz",
            "assets/decdnnf_phi_n_reduce/tddnnf/sdd/{type}/{density}.err",
            "assets/benchmarks/decdnnf_phi_n_reduce/tddnnf/sdd/{type}/{density}.jsonl"
        ],
        decdnnf_extend_n_reduce_d4=[
            "assets/decdnnf_extend_n_reduce/tddnnf/d4/{type}/{density}.t_reduced_phi.models.gz",
            "assets/decdnnf_extend_n_reduce/tddnnf/d4/{type}/{density}.err",
            "assets/benchmarks/decdnnf_extend_n_reduce/tddnnf/d4/{type}/{density}.jsonl"
        ],
        decdnnf_extend_n_reduce_sdd=[
            "assets/decdnnf_extend_n_reduce/tddnnf/sdd/{type}/{density}.t_reduced_phi.models.gz",
            "assets/decdnnf_extend_n_reduce/tddnnf/sdd/{type}/{density}.err",
            "assets/benchmarks/decdnnf_extend_n_reduce/tddnnf/sdd/{type}/{density}.jsonl"
        ],
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
            "assets/benchmarks/wmi/decdnnf/tddnnf/d4/noop/{type}/{density}.jsonl"
        ],
        wmi_decdnnf_sdd=[
            *["assets/wmi/decdnnf/tddnnf/sdd/noop/{type}/{density}." + suffix for suffix in ["out", "err", "steps"]],
            "assets/benchmarks/wmi/decdnnf/tddnnf/sdd/noop/{type}/{density}.jsonl"
        ],
        wmi_decdnnf_exists_x_d4=[
            *["assets/wmi/decdnnf_two_steps/exists_x/d4/noop/{type}/{density}." + suffix for suffix in ["out", "err", "steps"]],
            "assets/benchmarks/wmi/decdnnf_two_steps/exists_x/d4/noop/{type}/{density}.jsonl"
        ],
        wmi_decdnnf_exists_x_sdd=[
            *["assets/wmi/decdnnf_two_steps/exists_x/sdd/noop/{type}/{density}." + suffix for suffix in ["out", "err", "steps"]],
            "assets/benchmarks/wmi/decdnnf_two_steps/exists_x/sdd/noop/{type}/{density}.jsonl"
        ],
        wmi_decdnnf_exists_A_d4=[
            *["assets/wmi/decdnnf_two_steps/exists_A/d4/noop/{type}/{density}." + suffix for suffix in ["out", "err", "steps"]],
            "assets/benchmarks/wmi/decdnnf_two_steps/exists_A/d4/noop/{type}/{density}.jsonl"
        ],
        wmi_decdnnf_exists_A_sdd=[
            *["assets/wmi/decdnnf_two_steps/exists_A/sdd/noop/{type}/{density}." + suffix for suffix in ["out", "err", "steps"]],
            "assets/benchmarks/wmi/decdnnf_two_steps/exists_A/sdd/noop/{type}/{density}.jsonl"
        ],
        wmi_decdnnf_phi_n_reduce_d4=[
            *["assets/wmi/decdnnf_phi_n_reduce/tddnnf/d4/noop/{type}/{density}." + suffix for suffix in ["out", "err", "steps"]],
            "assets/benchmarks/wmi/decdnnf_phi_n_reduce/tddnnf/d4/noop/{type}/{density}.jsonl"
        ],
        wmi_decdnnf_phi_n_reduce_sdd=[
            *["assets/wmi/decdnnf_phi_n_reduce/tddnnf/sdd/noop/{type}/{density}." + suffix for suffix in ["out", "err", "steps"]],
            "assets/benchmarks/wmi/decdnnf_phi_n_reduce/tddnnf/sdd/noop/{type}/{density}.jsonl"
        ],
        wmi_decdnnf_extend_n_reduce_d4=[
            *["assets/wmi/decdnnf_extend_n_reduce/tddnnf/d4/noop/{type}/{density}." + suffix for suffix in ["out", "err", "steps"]],
            "assets/benchmarks/wmi/decdnnf_extend_n_reduce/tddnnf/d4/noop/{type}/{density}.jsonl"
        ],
        wmi_decdnnf_extend_n_reduce_sdd=[
            *["assets/wmi/decdnnf_extend_n_reduce/tddnnf/sdd/noop/{type}/{density}." + suffix for suffix in ["out", "err", "steps"]],
            "assets/benchmarks/wmi/decdnnf_extend_n_reduce/tddnnf/sdd/noop/{type}/{density}.jsonl"
        ],
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
    threads: 17
    resources:
        mem="20GB"
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
        mem="40GB"
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
        mem="40GB"
    input:
        mapping="assets/phi_with_tlemmas/{type}/{density}.mapping",
        sdd="assets/tddnnf/sdd/{type}/{density}.t_reduced_phi.min-sdd",
        vtree="assets/tddnnf/sdd/{type}/{density}.t_reduced_phi.min-vtree"
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
        vtree="assets/tddnnf/sdd/{type}/{density}.t_reduced_phi.min-vtree",
        sdd="assets/tddnnf/sdd/{type}/{density}.t_reduced_phi.min-sdd",
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


rule decdnnf_phi_n_reduce:
    threads: 26
    resources:
        disk="50GB"
    input:
        phi="assets/{nnf}.phi.min-nnf",
        t_reduced_phi="assets/{nnf}.t_reduced_phi.min-nnf"
    output:
        temp("assets/decdnnf_phi_n_reduce/{nnf}.t_reduced_phi.models")
    log:
        "assets/decdnnf_phi_n_reduce/{nnf}.err"
    benchmark:
        "assets/benchmarks/decdnnf_phi_n_reduce/{nnf}.jsonl"
    params:
        "src.decdnnf.decdnnf_n_ddnnife"
    shell:
        """
        if [[ -s {input.phi:q} && -s {input.t_reduced_phi:q} ]]; then
          timeout --verbose {config[timeout][enumerator]}m \
            python -m {params} \
            --cores {threads} \
            --output {output} \
            --phi {input.phi} \
            --t_reduced_phi {input.t_reduced_phi} \
            2> {log} \
            || touch {output}
        fi

        touch {output}
        """


rule decdnnf_extend_n_reduce:
    threads: 26
    resources:
        disk="50GB"
    input:
        t_extended_phi="assets/{nnf}.t_extended_phi.min-nnf",
        t_reduced_phi="assets/{nnf}.t_reduced_phi.min-nnf"
    output:
        temp("assets/decdnnf_extend_n_reduce/{nnf}.t_reduced_phi.models")
    log:
        "assets/decdnnf_extend_n_reduce/{nnf}.err"
    benchmark:
        "assets/benchmarks/decdnnf_extend_n_reduce/{nnf}.jsonl"
    params:
        "src.decdnnf.decdnnf_n_ddnnife"
    shell:
        """
        if [[ -s {input.t_extended_phi:q} && -s {input.t_reduced_phi:q} ]]; then
          timeout --verbose {config[timeout][enumerator]}m \
            python -m {params} \
            --cores {threads} \
            --output {output} \
            --phi {input.t_extended_phi} \
            --t_reduced_phi {input.t_reduced_phi} \
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
