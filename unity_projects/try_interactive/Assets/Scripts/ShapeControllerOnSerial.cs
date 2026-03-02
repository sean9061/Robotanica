using UnityEngine;

public class ShapeControllerOnSerial : MonoBehaviour
{
    public SkinnedMeshRenderer skinnedMeshRenderer;
    public int blendShapeIndex = 0; // Blenderのシェイプキー順
    string receive_data;
    float data;
    public SerialHandler serialHandler;

    void Start()
    {
        serialHandler.OnDataReceived += OnDataReceived;
    }

    //データを受信したら
    void OnDataReceived(string message)
    {
        receive_data = (message);           //受信データをreceive_dataに入れる
        data = float.Parse(receive_data);   //float型に変換してdataに入れる
        Debug.Log("受信データ: " + data);
    }
    
    void Update()
    {
        SetShapeKey(data);
    }
    
    // 0.0～1.0 の値で口の開閉
    public void SetShapeKey(float value)
    {
        skinnedMeshRenderer.SetBlendShapeWeight(blendShapeIndex, Mathf.Clamp01(value) * 100f);
    }
}
