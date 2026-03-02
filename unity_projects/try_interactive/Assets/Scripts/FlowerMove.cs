using System.Collections;
using System.Collections.Generic;
using UnityEngine;

public class FlowerMove : MonoBehaviour
{
    public UDPReceiver_ udp;
    public float moveScale;
    public float depthScale;
    private Vector3 startPos;
    // Start is called before the first frame update
    void Start()
    {
        startPos = transform.position;
    }

    // Update is called once per frame
    void Update()
    {
        float x = udp.latestData.x; //0~1
        float y = udp.latestData.y; //0~1
        float w = udp.latestData.w; //0~1
        float h = udp.latestData.h; //0~1
        float conf = udp.latestData.conf; //0~1

        float z = Mathf.Sqrt(w*w + h*h);

        x = -2*x + 1;
        y = -2*y + 1;
        z = z*depthScale;

        transform.position = new Vector3(x, y, z) * moveScale + startPos;
    }
}
