# 🌷 Kinetic-Botanics

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python)](https://www.python.org/)
[![Unity](https://img.shields.io/badge/Unity-2022%20LTS-000000?logo=unity)](https://unity.com/)
[![Arduino](https://img.shields.io/badge/Arduino-ESP32-00979D?logo=arduino)](https://www.arduino.cc/)
[![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Windows-lightgrey)](https://github.com)
[![MediaPipe](https://img.shields.io/badge/MediaPipe-0.10.14-00BCD4?logo=google)](https://mediapipe.dev/)
[![YOLO](https://img.shields.io/badge/YOLO-v2.6-00FFFF?logo=ultralytics)](https://docs.ultralytics.com/)

> コンピュータビジョン・ステッピングモーター制御・リアルタイム3D可視化を融合した、インタラクティブ体感型アートインスタレーション。

---

## 概要

手の「動き」を用いて植物の方向を物理的に操作し、そのダイナミクスを映像空間へとつなぎ人へと還すインタラクティブ作品です。

人と植物という有機物の間をロボティクスという無機物がつなぐ先に、現実とデジタルがリアルタイムに循環する、新しい操作体験を提示します。

---

## 特徴

- **手トラッキング（MediaPipe）**: 指先の距離と回転を極座標変換してモーター制御値を算出。カメラ距離による幅の変化を別骨格との比率で正規化
- **チューリップロボット（ESP32）**: 植物にワイヤーを取り付け、モーターで引っ張り・緩めることで方向を物理的に変える
- **チューリップ検出（YOLO + CoreML）**: 事前にチューリップの外見を学習させたカスタムモデルで植物の動きをトラッキングし、位置情報を Unity へ送信
- **Unity 3D 可視化**: キャラクターがチューリップに乗って運ばれるよう表現。キャラクターの状態によって移動やアニメーションが決定
- **リアルタイムダッシュボード**: 両カメラ映像・モーター値・検出データを1画面に集約。MJPEGストリーム＋UDP受信による多マシン対応
- **マルチマシン構成**: macOS × 2台（AIトラッキング）＋ Windows × 1台（Unity・ダッシュボード）を LAN で連携

---

## システム構成

![システム構成図](docs/system_image.svg)

```
mac2: Hand Tracker
  カメラ → MediaPipe → Serial (Arduino ESP32)
                    → UDP [dashboard_ip]:5100  (JSON: servo/polar/detected)
                    → HTTP 0.0.0.0:5102        (MJPEG 映像ストリーム)

mac3: Tulip Tracker
  カメラ → YOLO (CoreML) → UDP [unity_ip]:5004    (JSON → Unity)
                         → UDP [dashboard_ip]:5101 (JSON: x/y/w/h/conf/detected)
                         → HTTP 0.0.0.0:5103       (MJPEG 映像ストリーム)

win1: Unity + Dashboard
  Unity     ← UDP :5004
  Dashboard ← UDP :5100 / :5101
            ← http://[mac2_ip]:5102/  (手の映像)
            ← http://[mac3_ip]:5103/  (チューリップの映像)

Arduino ESP32
  ← Serial from mac2 (0xFF ヘッダ + radius + angle)
  GPIO 25, 26, 27 → ステッピングモーター3本
```

---

## 開発チーム

| メンバー | GitHub | 担当 |
|----------|--------|------|
| かっきー | [@kackason](https://github.com/kackason) | MediaPipe による手トラッキング実装・Unity 3D 可視化シーン構築 |
| しーすー | [@ta2ya225](https://github.com/ta2ya225) | Arduino ESP32 ファームウェア・ステッピングモーター機構・植物へのワイヤー取り付けなどハードウェア全般 |
| フィシャ | [@sean9061](https://github.com/sean9061) | YOLO によるチューリップ検出モデル・マルチマシン LAN 構成・リアルタイムダッシュボード開発 |

---

## 前提条件

### 共通
- Git

### mac2 / mac3 (Python 環境)
- Python 3.10 以上
- USB接続のWebカメラ
- （mac3のみ）Apple Silicon Mac（CoreML推論に必要）

### win1 (Unity + ダッシュボード)
- Unity 2022 LTS 以上
- Python 3.10 以上

### ハードウェア
- Arduino ESP32 開発ボード
- ステッピングモーター × 3
- スイッチングハブ（マルチマシン接続用）

---

## インストール

### 1. リポジトリのクローン

```bash
git clone https://github.com/sean9061/Kinetic-Botanics.git
cd Kinetic-Botanics
```

### 2. Hand Tracker のセットアップ（mac2）

```bash
cd ai/hand_tracker
pip install -r requirements.txt
```

### 3. Tulip Tracker のセットアップ（mac3）

```bash
cd ai/tulip_tracker
pip install -r requirements.txt
```

### 4. ダッシュボードのセットアップ（win1）

```bash
cd dashboard
pip install -r requirements.txt
```

### 5. Arduino ファームウェアの書き込み

Arduino IDE で `hardware/arduino_from_mediapipe.ino` を ESP32 に書き込みます（ボーレート: 115200）。

ライブラリ: `ESP32Servo`（Arduino IDE のライブラリマネージャーからインストール）

### 6. Unity プロジェクトを開く

Unity Hub から `unity_projects/try_interactive/` を Unity 2022 LTS で開きます。

---

## 設定

各スクリプトの先頭にある定数を環境に合わせて変更してください。

| ファイル | 定数 | 説明 |
|---------|------|------|
| `ai/hand_tracker/mediapipe_to_arduino.py` | `SERIAL_PORT` | ArduinoのCOMポート（例: `/dev/tty.usbserial-0001`） |
| `ai/hand_tracker/mediapipe_to_arduino.py` | `DASHBOARD_IP` | ダッシュボードを動かすマシンのIPアドレス |
| `ai/tulip_tracker/predict.py` | `DASHBOARD_IP` | 同上 |
| `ai/tulip_tracker/predict.py` | `UNITY_HOST` | UnityマシンのIPアドレス |

---

## 使い方

本番環境では各マシンで以下を起動します。

### mac2: Hand Tracker

```bash
cd ai/hand_tracker
python mediapipe_to_arduino.py
# カメラ映像ウィンドウが開き、右手を検出するとステッピングモーターが動きます
# ESC キーで終了
```

### mac3: Tulip Tracker

```bash
cd ai/tulip_tracker
python predict.py
# カメラ映像とYOLO検出結果がウィンドウに表示されます
# スライダーで検出閾値を調整できます (デフォルト: 80%)
# q キーで終了
```

### win1: ダッシュボード（本番）

```bash
python dashboard/dashboard.py --hand-host [mac2のIP] --tulip-host [mac3のIP]
```

### ローカルテスト（1台で全部動かす場合）

各スクリプトの `DASHBOARD_IP` を `127.0.0.1` に変更した上で:

```bash
# ターミナル1
python ai/hand_tracker/mediapipe_to_arduino.py

# ターミナル2
python ai/tulip_tracker/predict.py

# ターミナル3
python dashboard/dashboard.py --hand-host 127.0.0.1 --tulip-host 127.0.0.1
```

### Unity シーン

`unity_projects/try_interactive/Assets/Scenes/` から用途に合わせてシーンを選択:

| シーン | 内容 |
|--------|------|
| `UDP Interactive.unity` | 花の位置でオブジェクトをインタラクティブ制御 |
| `UDP Dwarf.unity` | ドワーフキャラクターを制御 |
| `UDP Joint.unity` | 骨格アニメーション |
| `Serial Interactive.unity` | シリアル（Arduino）による制御 |

---
## ディレクトリ構成

```
Kinetic-Botanics/
├── ai/
│   ├── hand_tracker/
│   │   ├── mediapipe_to_arduino.py   # MediaPipe手検出 → Serial/UDP/MJPEG
│   │   └── requirements.txt
│   └── tulip_tracker/
│       ├── predict.py                # YOLO花検出 → UDP/MJPEG
│       ├── export.py                 # PyTorch → CoreML変換
│       ├── udp_receiver_test.py      # UDP受信テスト
│       ├── best.pt                   # 学習済みモデル (PyTorch)
│       ├── best.mlpackage/           # 学習済みモデル (CoreML)
│       └── requirements.txt
├── dashboard/
│   ├── dashboard.py                  # リアルタイム監視ダッシュボード
│   └── requirements.txt
├── hardware/
│   └── arduino_from_mediapipe.ino    # ESP32 ファームウェア
└── unity_projects/
    └── try_interactive/
        └── Assets/
            ├── Scenes/               # インタラクティブシーン (5種)
            └── Scripts/              # C#スクリプト (24ファイル)
```


## ライセンス

このプロジェクトは **MIT License** のもとで公開されています。詳細は [LICENSE](LICENSE) ファイルをご確認ください。

---

<sub>💡 README の構成は <a href="https://claude.ai/code">Claude Code</a> との対話を通じて作成されました。</sub>
