import subprocess
import json
import os
import argparse

def get_audio_stream_count(filepath):
    """
    指定されたメディアファイルの音声ストリーム数を取得します。

    Args:
        filepath (str): メディアファイルのパス。

    Returns:
        int: 音声ストリームの数。エラー時は -1 を返します。
    """
    command = [
        'ffprobe',
        '-v', 'quiet',
        '-print_format', 'json',
        '-show_streams',
        '-select_streams', 'a',  # 音声ストリームのみを選択
        filepath
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True, encoding='utf-8')
        streams_info = json.loads(result.stdout)
        return len(streams_info.get('streams', []))
    except FileNotFoundError:
        print("エラー: ffprobe が見つかりません。FFmpegが正しくインストールされ、パスが通っているか確認してください。")
        return -1
    except subprocess.CalledProcessError as e:
        print(f"ffprobe の実行中にエラーが発生しました: {e}")
        if e.stderr:
            print(f"エラー詳細:\n{e.stderr.strip()}")
        return -1
    except json.JSONDecodeError:
        print("エラー: ffprobe の出力 (JSON形式) の解析に失敗しました。")
        return -1
    except Exception as e:
        print(f"予期せぬエラーが発生しました (get_audio_stream_count): {e}")
        return -1

def extract_audio_tracks(mp4_filepath, output_dir=None):
    """
    MP4ファイルから全ての音声トラックを個別のWAVファイルとして抽出します。

    Args:
        mp4_filepath (str): 入力するMP4ファイルのパス。
        output_dir (str, optional): WAVファイルの出力先ディレクトリ。
                                     指定しない場合、入力ファイルと同じディレクトリに出力します。
    """
    if not os.path.isfile(mp4_filepath):
        print(f"エラー: 入力ファイル '{mp4_filepath}' が見つかりません。パスを確認してください。")
        return

    print(f"処理中のファイル: {mp4_filepath}")
    num_audio_tracks = get_audio_stream_count(mp4_filepath)

    if num_audio_tracks <= 0:
        if num_audio_tracks == 0:
            print(f"'{mp4_filepath}' には抽出可能な音声トラックが見つかりませんでした。")
        # num_audio_tracksが-1の場合は、get_audio_stream_count内でエラーメッセージが表示されています
        return

    print(f"'{mp4_filepath}' には {num_audio_tracks} 個の音声トラックが見つかりました。抽出を開始します...")

    base_filename = os.path.splitext(os.path.basename(mp4_filepath))[0]

    if output_dir is None:
        output_dir = os.path.dirname(os.path.abspath(mp4_filepath))
    else:
        # output_dirが指定された場合、そのディレクトリが存在しなければ作成
        if not os.path.exists(output_dir):
            try:
                os.makedirs(output_dir, exist_ok=True)
                print(f"出力ディレクトリ '{output_dir}' を作成しました。")
            except OSError as e:
                print(f"エラー: 出力ディレクトリ '{output_dir}' の作成に失敗しました: {e}")
                return


    successful_extractions = 0
    for i in range(num_audio_tracks):
        output_filename = f"{base_filename}_track_{i}.wav"
        output_filepath = os.path.join(output_dir, output_filename)

        # ffmpeg コマンドを構築
        # -map 0:a:i は i番目の音声ストリームを選択 (0から始まるインデックス)
        # -c:a pcm_s16le は標準的なWAV形式 (16-bit PCM) で出力
        command = [
            'ffmpeg',
            '-y',  # 出力ファイルが既に存在する場合、確認なしで上書き
            '-i', mp4_filepath,
            '-map', f'0:a:{i}',
            '-c:a', 'pcm_s16le',
            output_filepath
        ]

        print(f"  トラック {i} を '{output_filepath}' に抽出中...")
        try:
            # stderrとstdoutをキャプチャするが、エラー時のみ表示
            process = subprocess.run(command, capture_output=True, text=True, check=True, encoding='utf-8')
            print(f"  トラック {i} の抽出が完了しました。")
            successful_extractions +=1
        except FileNotFoundError:
            print("エラー: ffmpeg が見つかりません。FFmpegが正しくインストールされ、パスが通っているか確認してください。")
            return # ffmpegが見つからない場合は処理を中断
        except subprocess.CalledProcessError as e:
            print(f"  トラック {i} の抽出中にエラーが発生しました。")
            print(f"  コマンド: {' '.join(command)}")
            # ffmpegのエラー出力はstderrにあることが多い
            if e.stderr:
                print(f"  FFmpegエラー出力:\n{e.stderr.strip()}")
            else:
                print(f"  エラー詳細: {e}") # stderrがない場合
        except Exception as e:
            print(f"  トラック {i} の抽出中に予期せぬエラーが発生しました: {e}")
            print(f"  コマンド: {' '.join(command)}")


    if successful_extractions == num_audio_tracks and num_audio_tracks > 0:
        print(f"\n全ての音声トラック ({successful_extractions}個) の抽出が完了しました。")
        print(f"出力先ディレクトリ: {os.path.abspath(output_dir)}")
    elif successful_extractions > 0:
        print(f"\n{successful_extractions}個の音声トラックの抽出が完了しましたが、一部エラーが発生した可能性があります。")
        print(f"出力先ディレクトリ: {os.path.abspath(output_dir)}")
    elif num_audio_tracks > 0 : # num_audio_tracks > 0 だが successful_extractions == 0
        print("\n音声トラックの抽出に全て失敗しました。上記のエラーメッセージを確認してください。")
    # num_audio_tracks <= 0 の場合は既に対応済み

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="マルチトラック音声のMP4ファイルから個別のWAVファイルを抽出します。\nFFmpegとffprobeがインストールされ、パスが通っている必要があります。",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("input_mp4", help="処理対象のMP4ファイルパス。")
    parser.add_argument(
        "-o", "--output_dir",
        help="WAVファイルの出力先ディレクトリ。\n指定しない場合は、入力ファイルと同じディレクトリに出力します。",
        default=None
    )

    args = parser.parse_args()

    extract_audio_tracks(args.input_mp4, args.output_dir)
