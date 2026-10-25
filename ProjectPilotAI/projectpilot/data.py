"""Synthetic, clearly-labelled historical task data used to train the delay model.

No real project data is used. Delay probability is generated from a latent
risk formula plus noise, so the model learns realistic relationships
(long tasks, overloaded owners, no slack and skill mismatch raise delay risk).
"""
import numpy as np
import pandas as pd

FEATURES = ["duration", "n_deps", "owner_load", "slack", "skill_match", "progress_gap", "team_size"]


def generate(n: int = 4000, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    df = pd.DataFrame({
        "duration": rng.integers(1, 16, n),
        "n_deps": rng.integers(0, 5, n),
        "owner_load": rng.uniform(10, 130, n),
        "slack": rng.integers(0, 12, n),
        "skill_match": rng.integers(0, 2, n),
        "progress_gap": rng.uniform(0, 0.6, n),
        "team_size": rng.integers(2, 12, n),
    })
    z = (-3.4 + 0.12 * df.duration + 0.28 * df.n_deps + 0.022 * df.owner_load
         - 0.25 * df.slack + 0.9 * (1 - df.skill_match) + 3.2 * df.progress_gap
         - 0.05 * df.team_size + rng.normal(0, 0.6, n))
    df["delayed"] = (rng.uniform(size=n) < 1 / (1 + np.exp(-z))).astype(int)
    return df


if __name__ == "__main__":
    d = generate()
    d.to_csv("data/synthetic_tasks.csv", index=False)
    print(d.shape, "delay rate:", round(d.delayed.mean(), 3))
