using UnityEngine;

public class FlowerMove : MonoBehaviour
{
    public UDPReceiver_ udp;

    public float moveScale = 1f;
    public float depthScale = 1f;

    public Vector3 moveRange = new Vector3(1,1,1);

    private Vector3 startPos;
    float x,y,w,h,z;


    void Start()
    {
        startPos = transform.position;
    }

    void Update()
    {
        x = udp.latestData.x;
        y = udp.latestData.y;
        w = udp.latestData.w;
        h = udp.latestData.h;

        z = Mathf.Sqrt(w*w + h*h);

        x = -2*x + 1;
        y = -2*y + 1;
        z = z * depthScale;

        Vector3 targetPos = new Vector3(x, 0, 0);
        targetPos = Vector3.Scale(targetPos, moveRange) + startPos;
        transform.position = targetPos;

    }

    
}