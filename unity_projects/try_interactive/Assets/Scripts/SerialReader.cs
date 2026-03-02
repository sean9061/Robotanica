using UnityEngine;
using System.IO.Ports;
using System.Threading;

public class SerialReader : MonoBehaviour
{
    public string portName = "COM7"; // 実際のポートに合わせて
    public int baudRate = 115200;

    private SerialPort serial;
    private Thread readThread;
    private bool running = false;

    public Vector2 joystickValue = Vector2.zero; // 0〜1に正規化された値

    void Start()
    {
        try
        {
            serial = new SerialPort(portName, baudRate);
            serial.ReadTimeout = 100;
            serial.Open();

            running = true;
            readThread = new Thread(ReadSerial);
            readThread.Start();

            Debug.Log($"✅ Serial port {portName} opened.");
        }
        catch (System.Exception e)
        {
            Debug.LogError($"❌ Failed to open {portName}: {e.Message}");
        }
    }

    void ReadSerial()
    {
        while (running && serial != null && serial.IsOpen)
        {
            try
            {
                string line = serial.ReadLine().Trim();
                string[] parts = line.Split(',');

                if (parts.Length == 2 &&
                    float.TryParse(parts[0], out float rawX) &&
                    float.TryParse(parts[1], out float rawY))
                {
                    joystickValue = new Vector2(
                        Mathf.Clamp01(rawX / 4095f),
                        Mathf.Clamp01(rawY / 4095f)
                    );
                }
            }
            catch (System.TimeoutException)
            {
                // データがまだ来ていないだけ
            }
            catch (System.Exception e)
            {
                Debug.LogWarning($"Serial read error: {e.Message}");
            }
        }
    }

    void OnApplicationQuit()
    {
        running = false;
        Thread.Sleep(100);

        if (serial != null)
        {
            if (serial.IsOpen)
                serial.Close();

            serial.Dispose();
            serial = null;
        }

        if (readThread != null && readThread.IsAlive)
            readThread.Join();

        Debug.Log("🔌 Serial port closed safely.");
    }
}
