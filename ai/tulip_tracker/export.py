from ultralytics import YOLO

# Macにコピーしてきた best.pt を読み込む
model = YOLO('best.pt')

# Mac上でCoreMLに変換！
model.export(format='coreml')