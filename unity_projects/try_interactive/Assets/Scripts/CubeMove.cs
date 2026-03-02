using System.Collections;
using System.Collections.Generic;
using UnityEngine;

public class CubeMove : MonoBehaviour
{
    public float moveSpeed;
    public float rotSpeed;
    public float jumpPower;
    Rigidbody rb;
    // Start is called before the first frame update
    void Start()
    {
        rb = GetComponent<Rigidbody>();
    }

    // Update is called once per frame
    void Update()
    {
        float hrz = Input.GetAxis("Horizontal");
        float vrt = Input.GetAxis("Vertical");
        transform.Rotate(0, rotSpeed*hrz,0);
        transform.position += transform.forward * moveSpeed * vrt;
        if (Input.GetKeyDown(KeyCode.Space))
        {
            rb.AddForce(new Vector3(0,jumpPower,0),ForceMode.Impulse);
        }
    }
}
