using UnityEngine;

public class DwarfController : MonoBehaviour
{
    // [Header("Movement")]
    public float moveSpeed = 2f;
    public float areaRadius = 5f;
    public Transform areaCenter;

    // [Header("Avoid Tentacle")]
    public Transform tentacleRoot;
    public float avoidRadius = 1.5f;
    public float avoidStrength = 3f;

    // [Header("Health")]
    public float maxHealth = 100f;
    public float rainDamagePerSecond = 10f;

    float health;
    Vector3 targetPos;
    bool inRain = false;

    void Start()
    {
        health = maxHealth;
        PickNewTarget();
    }

    void Update()
    {
        Move();
        HandleDamage();
    }

    void Move()
    {
        Vector3 dir = (targetPos - transform.position);

        if (dir.magnitude < 0.3f)
            PickNewTarget();

        dir = dir.normalized;

        // 触手回避
        if (tentacleRoot != null)
        {
            Vector3 toTentacle = transform.position - tentacleRoot.position;
            float dist = toTentacle.magnitude;

            if (dist < avoidRadius)
            {
                Vector3 avoidDir = toTentacle.normalized;
                dir += avoidDir * avoidStrength;
            }
        }

        dir = dir.normalized;

        transform.position += dir * moveSpeed * Time.deltaTime;

        if (dir != Vector3.zero)
            transform.forward = dir;
    }

    void PickNewTarget()
    {
        Vector2 rand = Random.insideUnitCircle * areaRadius;
        targetPos = areaCenter.position + new Vector3(rand.x, 0, rand.y);
    }

    void HandleDamage()
    {
        if (inRain)
        {
            health -= rainDamagePerSecond * Time.deltaTime;
            health = Mathf.Clamp(health, 0, maxHealth);
        }
    }

    void OnParticleCollision(GameObject other)
    {
        // 雨に当たったらフラグON
        inRain = true;
    }

    void LateUpdate()
    {
        // フレーム毎にリセット
        inRain = false;
    }
}
