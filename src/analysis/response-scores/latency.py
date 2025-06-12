import pandas as pd
import matplotlib.pyplot as plt
from argparse import ArgumentParser
from pathlib import Path

def load_and_flatten_jsonl(file_path: Path) -> pd.DataFrame:
    df = pd.read_json(file_path, lines=True)
    # Flatten the nested response field
    response_data = pd.json_normalize(df['response'].apply(lambda r: r[0] if isinstance(r, list) and r else {}))
    df_flat = pd.concat([df.drop(columns='response'), response_data], axis=1)
    return df_flat

def compute_latency_stats(df: pd.DataFrame) -> pd.DataFrame:
    latencies = df['latency']
    stats = {
        'Total Responses': len(latencies),
        'Total Time (minutes)': latencies.sum() / 60,
        'Min Latency (seconds)': latencies.min(),
        'Max Latency (seconds)': latencies.max(),
        'Average Latency (seconds)': latencies.mean(),
        'Median Latency (seconds)': latencies.median()
    }
    return pd.DataFrame(list(stats.items()), columns=['Metric', 'Value'])

def plot_latency_stats(stats_df: pd.DataFrame, output_path: Path):
    plt.figure(figsize=(10, 6))
    bars = plt.barh(stats_df['Metric'], stats_df['Value'], color='skyblue')
    plt.xlabel('Value')
    plt.title('Latency Summary')
    plt.grid(True, linestyle='dotted', axis='x', alpha=0.5)

    for bar in bars:
        width = bar.get_width()
        plt.text(width, bar.get_y() + bar.get_height() / 2, f'{width:.2f}', va='center')

    plt.tight_layout()
    plt.savefig(output_path)
    print(f"Saved plot to {output_path}")

if __name__ == '__main__':
    parser = ArgumentParser(description="Plot latency summary from a JSONL file.")
    parser.add_argument('--input', type=Path, required=True, help="Path to the .jsonl file")
    parser.add_argument('--output', type=Path, default=Path("latency_summary.png"), help="Path to save the output plot")
    args = parser.parse_args()

    df = load_and_flatten_jsonl(args.input)
    stats_df = compute_latency_stats(df)
    plot_latency_stats(stats_df, args.output)
