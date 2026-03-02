using System.Net;
using System.Net.Sockets;
using System.Text;
using UnityEngine;

public class UDPReceiver_ : MonoBehaviour
{
    UdpClient client;
    IPEndPoint ep;
    public int portNum = 5004;
    public Datas latestData;
    void Start()
    {
        // client = new UdpClient(portNum);
        // ep = new IPEndPoint(IPAddress.Any, 0);

        // Debug.Log("Listening on port: " + portNum);

        // client.BeginReceive(Receive, null);

        client = new UdpClient(portNum);
        Debug.Log("AddressFamily: " + client.Client.AddressFamily);
        ep = new IPEndPoint(IPAddress.Any, 0);
        client.BeginReceive(Receive, null); // BeginRceive|Receive

        Debug.Log("Start");
    }

    void Receive(System.IAsyncResult ar)
    {
        Debug.Log("Connected");
        byte[] data = client.EndReceive(ar, ref ep);
        string json = Encoding.UTF8.GetString(data);
        Debug.Log(json);
        Datas parsed = JsonUtility.FromJson<Datas>(json);
        latestData = parsed;

        client.BeginReceive(Receive, null);
    }

    void OnApplicationQuit()
    {
        if(client != null)
        {
            client.Close();
            client = null;
            Debug.Log("ポート解放");
        }
    }
}
