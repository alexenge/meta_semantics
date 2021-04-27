# ---
# jupyter:
#   jupytext:
#     formats: py:percent
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.11.1
#   kernelspec:
#     display_name: Python 3
#     language: python
#     name: python3
# ---

# %%
from glob import glob
from os import makedirs, path, remove
from re import sub
from subprocess import run

import numpy as np
import pandas as pd
from atlasreader import get_statmap_info
from nilearn import image, reporting
from nimare.utils import mni2tal

# %%
# Read included experiments (Table 1)
exps = pd.read_json("../results/exps.json")
exps["foci"] = [np.array(foci, dtype="float") for foci in exps["foci"]]
exps["n_foci"] = [len(foci) for foci in exps["foci"]]

# Compute summary statistics
_ = [
    print(
        col + ":",
        "sum",
        exps[col].sum(),
        "mean",
        exps[col].mean(),
        "median",
        exps[col].median(),
        "min",
        exps[col].min(),
        "max",
        exps[col].max(),
    )
    for col in ["n", "age_mean", "age_min", "age_max", "n_foci"]
]

# Compute weighted mean age
exps["age_mean_weighted"] = [age * n for age, n in zip(exps["age_mean"], exps["n"])]
print("weighted mean age:", exps["age_mean_weighted"].sum() / exps["n"].sum())

# Compute sex and handedness ratios
print(exps["sex_female"].sum() / (exps["sex_female"].sum() + exps["sex_male"].sum()))
print(exps["hand_right"].sum() / (exps["hand_right"].sum() + exps["hand_left"].sum()))

# Count peaks with and without effect sizes
tstats = exps["tstats_corr"].explode()
print(len(tstats[tstats != "p"]))
print(len(tstats[tstats != "p"]) / len(tstats))
print(len(tstats[tstats == "p"]))

# Cut peaks in left vs. right hemisphere
foci = exps["foci_mni"].explode()
foci_x = [focus[0] for focus in foci]
foci_left = [x for x in foci_x if x < 0]
print(len(foci_left))
print(len(foci_left) / len(foci_x))

# %%
# Define function to print the clusters from multiple images as a table
def combined_cluster_table(
    img_files_z=[],
    img_files_ale=[],
    stub_keys=[],
    stub_colname="Analysis",
    atlas="aal",
    td_jar=None,
    output_file="cluster_table.tsv",
):

    # Create output director
    output_dir = path.dirname(output_file)
    makedirs(output_dir, exist_ok=True)

    # Create a list of DataFrames with peak and cluster stats for each image
    df_tuples = [
        get_statmap_info(img_file, cluster_extent=0, atlas="aal", voxel_thresh=0)
        for img_file in img_files_z
    ]
    dfs = [
        pd.DataFrame(
            {
                "Cluster #": df_tuple[0]["cluster_id"],
                "Size (mm3)": df_tuple[0]["volume_mm"],
                "Cluster labels": df_tuple[0][atlas],
                "Mean z": df_tuple[0]["cluster_mean"],
                "Peak z": df_tuple[1]["peak_value"],
                "Peak X": df_tuple[1]["peak_x"],
                "Peak Y": df_tuple[1]["peak_y"],
                "Peak Z": df_tuple[1]["peak_z"],
                "Peak label": df_tuple[1][atlas],
            }
        )
        for df_tuple in df_tuples
    ]

    # Add ALE values if available
    if img_files_ale:
        df_tuples_ale = [
            get_statmap_info(img_file, cluster_extent=0, atlas="aal", voxel_thresh=0)
            if img_file
            else (
                pd.DataFrame({"cluster_mean": [float("nan")]}),
                pd.DataFrame({"peak_value": [float("nan")]}),
            )
            for img_file in img_files_ale
        ]
        dfs_ale = [
            pd.DataFrame(
                {
                    "Mean ALE": df_tuple[0]["cluster_mean"],
                    "Peak ALE": df_tuple[1]["peak_value"],
                }
            )
            for df_tuple in df_tuples_ale
        ]
        for df, df_ale in zip(dfs, dfs_ale):
            df.insert(4, column="Mean ALE", value=df_ale["Mean ALE"])
            df.insert(6, column="Peak ALE", value=df_ale["Peak ALE"])

    # Concatenate into one big DataFrame
    df = pd.concat(dfs, keys=stub_keys)

    # Reformat numerical columns
    df["Size (mm3)"] = df["Size (mm3)"].apply(lambda x: "{:,.0f}".format(x))
    cols_int = ["Cluster #", "Peak X", "Peak Y", "Peak Z"]
    df[cols_int] = df[cols_int].applymap(int)
    cols_2f = ["Mean z", "Peak z"]
    df[cols_2f] = df[cols_2f].applymap(lambda x: "{:,.2f}".format(x))
    if img_files_ale:
        cols_3f = ["Mean ALE", "Peak ALE"]
        df[cols_3f] = df[cols_3f].applymap(lambda x: "{:,.3f}".format(x))
        df[cols_3f] = df[cols_3f].replace("nan", "")

    # Add the stub column
    df.index = df.index.set_names(stub_colname, level=0)
    df.reset_index(level=stub_colname, inplace=True)
    mask = df[stub_colname].duplicated()
    df.loc[mask.values, [stub_colname]] = ""

    # Save to CSV
    df.to_csv(output_file, sep="\t", index=False)

    return df


# %%
# Create Table 2 (ALE & SDM results)
tab2 = combined_cluster_table(
    img_files_z=[
        "../results/ale/all_z_thresh.nii.gz",
        "../results/sdm/analysis_mod1/mod1_z_thresh.nii.gz",
        "../results/sdm/analysis_mod2/mod2_z_thresh.nii.gz",
    ],
    stub_keys=[
        "Activation likelihood estimation",
        "Seed-based d mapping",
        "With covariates",
    ],
    stub_colname="Analysis",
    img_files_ale=[
        "../results/ale/all_stat_thresh.nii.gz",
        None,
        None,
    ],
    atlas="aal",
    output_file="../results/tables/tab2_children.tsv",
)
display(tab2)

# %%
# Create Table 3 (task category ALEs)
tab3 = combined_cluster_table(
    img_files_z=[
        "../results/ale/knowledge_z_thresh.nii.gz",
        "../results/ale/relatedness_z_thresh.nii.gz",
        "../results/ale/objects_z_thresh.nii.gz",
    ],
    stub_keys=[
        "Knowledge",
        "Relatedness",
        "Objects",
    ],
    stub_colname="Analysis",
    img_files_ale=[
        "../results/ale/knowledge_stat_thresh.nii.gz",
        "../results/ale/relatedness_stat_thresh.nii.gz",
        "../results/ale/objects_stat_thresh.nii.gz",
    ],
    atlas="aal",
    output_file="../results/tables/tab3_tasks.tsv",
)
display(tab3)

# %%
# Create Table 4 (differences between task categories)
tab4 = combined_cluster_table(
    img_files_z=[
        "../results/subtraction/knowledge_minus_nknowledge_z_thresh.nii.gz",
        "../results/subtraction/relatedness_minus_nrelatedness_z_thresh.nii.gz",
        "../results/subtraction/objects_minus_nobjects_z_thresh.nii.gz",
    ],
    stub_keys=[
        "Knowledge > (relatedness + objects)",
        "Relatedness > (knowledge + objects)",
        "Objects > (knowledge + relatedness)",
    ],
    stub_colname="Subtraction",
    atlas="aal",
    output_file="../results/tables/tab4_subtraction.tsv",
)
display(tab4)

# %%
# Create Table 5 (age-related changes)
tab5 = combined_cluster_table(
    img_files_z=["../results/subtraction/older_minus_younger_z_thresh.nii.gz"],
    stub_keys=["Older > younger"],
    stub_colname="Contrast",
    img_files_ale=[None],
    atlas="aal",
    output_file="../results/tables/tab5_age.tsv",
)
display(tab5)

# %%
# Create Table 5 (adults)
tab6 = combined_cluster_table(
    img_files_z=[
        "../results/adults/adults_z_thresh.nii.gz",
        "../results/adults/children_greater_adults_z_thresh.nii.gz",
        "../results/adults/adults_greater_children_z_thresh.nii.gz",
        "../results/adults/children_conj_adults_z.nii.gz",
    ],
    stub_keys=["Adults", "Children > adults", "Adults > children", "Conjunction"],
    stub_colname="Analysis",
    img_files_ale=["../results/adults/adults_stat_thresh.nii.gz", None, None],
    atlas="aal",
    output_file="../results/tables/tab6_adults.tsv",
)
display(tab6)

# %%
# Extract jackknife and FSN values from peaks
def extract_value_at_peaks(img_peaks, img_values, colname_value):

    # Extract original peak coordinates
    img_peaks = image.load_img(img_peaks)
    df, _ = get_statmap_info(img_peaks, cluster_extent=0, atlas="aal")
    x, y, z = [df[col] for col in ["peak_x", "peak_y", "peak_z"]]

    # Convert from MNI to array space
    affine = np.linalg.inv(img_peaks.affine)
    coords_ijk = image.coord_transform(x, y, z, affine=affine)
    coords_ijk = np.array(coords_ijk, dtype="int").T

    # Extract values at these peaks from the other image
    img_values = image.load_img(img_values)
    dat = img_values.get_fdata()
    peak_values = [dat[tuple(coords_ijk[ix])] for ix in range(len(coords_ijk))]

    # Append to table and return
    df[colname_value] = peak_values

    return df


# %%
# Apply to retrieve the jackknife values
prefixes = ["all", "knowledge", "relatedness", "objects"]
imgs_peaks = ["../results/ale/" + prefix + "_z_thresh.nii.gz" for prefix in prefixes]
imgs_values = [
    "../results/jackknife/" + prefix + "/mean_jk.nii.gz" for prefix in prefixes
]
dfs_jk = [
    extract_value_at_peaks(img_peaks, img_values, colname_value="jk")
    for img_peaks, img_values in zip(imgs_peaks, imgs_values)
]

# Display mean jackknife values and range
for i in range(len(prefixes)):
    print("Mean:", dfs_jk[i]["jk"].mean())
    print("Range:", dfs_jk[i]["jk"].min(), "–", dfs_jk[i]["jk"].max())

# %%
# Apply to retrieve the FSN values
imgs_peaks = ["../results/ale/" + prefix + "_z_thresh.nii.gz" for prefix in prefixes]
imgs_values = [
    "../results/fsn/" + prefix + "/" + prefix + "_mean_fsn.nii.gz"
    for prefix in prefixes
]
dfs_fsn = [
    extract_value_at_peaks(img_peaks, img_values, colname_value="fsn")
    for img_peaks, img_values in zip(imgs_peaks, imgs_values)
]

# Display mean jackknife values and range
for i in range(len(prefixes)):
    print("Mean:", dfs_fsn[i]["fsn"].mean())
    print("Range:", dfs_fsn[i]["fsn"].min(), "–", dfs_fsn[i]["fsn"].max())