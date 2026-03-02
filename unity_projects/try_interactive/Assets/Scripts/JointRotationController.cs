using UnityEngine;

public class JointRotationController : MonoBehaviour
{
    public Transform[] joints;   // 根元→先端
    public float maxBend = 15f;

    float[] angles = {0, 2*Mathf.PI/3, 4*Mathf.PI/3};

    void Update()
    {
        float x = Input.GetAxis("Horizontal");
        float y = Input.GetAxis("Vertical");

        float r = Mathf.Clamp01(Mathf.Sqrt(x*x + y*y));
        float theta = Mathf.Atan2(y, x);

        float[] contrib = new float[3];
        float mean = 0;

        // ワイヤ寄与計算
        for(int i=0;i<3;i++)
        {
            contrib[i] = r * Mathf.Cos(theta - angles[i]);
            mean += contrib[i];
        }

        mean /= 3f;

        for(int i=0;i<3;i++)
            contrib[i] -= mean;

        // ===== 曲げベクトル生成 =====
        Vector2 bend = Vector2.zero;

        for(int i=0;i<3;i++)
        {
            Vector2 dir = new Vector2(
                Mathf.Cos(angles[i]),
                Mathf.Sin(angles[i])
            );
            bend += dir * contrib[i];
        }

        // ===== Joint回転 =====
        for(int j=0; j<joints.Length; j++)
        {
            float t = 1f - (float)j / joints.Length; // 根元強く

            float bendX = bend.y * maxBend * t;
            float bendZ = -bend.x * maxBend * t;

            joints[j].localRotation =
                Quaternion.Euler(bendX, 0, bendZ);
        }
    }
}
