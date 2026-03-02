using UnityEngine;

public class ShapeControllerOnUdp : MonoBehaviour
{
    public UdpReceiver udp;
    public SkinnedMeshRenderer skinnedMeshRenderer;
    public int blendShapeIndex = 0; // Blenderのシェイプキー順
    public float distance;
    public float angle;
    
    
    void Update()
    {
        distance = udp.latestData.d * 0.5f;
        angle = udp.latestData.a;
        Vector3 worldangle = transform.eulerAngles;
        worldangle.y = angle;
        transform.eulerAngles = worldangle;
        SetShapeKey(100 - distance);
    }
    // 0.0～1.0 の値で口の開閉
    public void SetShapeKey(float value)
    {
        skinnedMeshRenderer.SetBlendShapeWeight(blendShapeIndex, value );
    }
}
