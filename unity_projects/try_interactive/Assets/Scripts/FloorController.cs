using UnityEngine;

public class FloorController : MonoBehaviour
{
    public float leanPower;
    public Vector2 grad;
    public SerialHandler serialHandler;

    void Start()
    {
        serialHandler.OnDataReceived += OnDataReceived;
    }

    //データを受信したら
    private void OnDataReceived(string message)
    {
        Debug.Log("受信データ: " + message);

        try
        {
            string[] values = message.Trim().Split(',');
            if (values.Length == 2)
            {
                float joyX, joyY;

                if (float.TryParse(values[0], out joyX) &&
                    float.TryParse(values[1], out joyY)
                )
                {
                    grad = new Vector2(joyX-0.5f, joyY-0.5f)*2;
                }
                else
                {
                    Debug.LogWarning("データ解析失敗: " + message);
                }
            }
        }
        catch (System.Exception e)
        {
            Debug.LogWarning("データ変換エラー: " + e.Message);
        }
    }
    
    void Update()
    {
        transform.eulerAngles = new Vector3(grad.x, 0, -grad.y)* leanPower;
    }
}
