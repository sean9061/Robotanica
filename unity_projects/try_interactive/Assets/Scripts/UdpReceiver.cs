using System.Net;
using System.Net.Sockets;
using System.Text;
using UnityEngine;

public class UdpReceiver : MonoBehaviour
{
    UdpClient client;
    IPEndPoint ep;
    public HandData latestData;
    void Start()
    {
        client = new UdpClient(5005);
        ep = new IPEndPoint(IPAddress.Any, 0);
        client.BeginReceive(Receive, null);
    }

    void Receive(System.IAsyncResult ar)
    {
        byte[] data = client.EndReceive(ar, ref ep);
        string json = Encoding.UTF8.GetString(data);
        Debug.Log(json);
        HandData parsed = JsonUtility.FromJson<HandData>(json);
        latestData = parsed;

        client.BeginReceive(Receive, null);
    }
}
