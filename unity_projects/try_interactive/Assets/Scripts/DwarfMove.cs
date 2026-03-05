using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.AI;

public class DwarfMove : MonoBehaviour
{
    private Transform flower;
    private Transform goal;
    private Rigidbody rb;

    enum State
    {
        LeftCliff,
        OnFlower,
        RightCliff,
        Jumping
    }

    private State state = State.Jumping;

    void Start()
    {
        flower = GameObject.Find("Flower").GetComponent<Transform>();
        goal = GameObject.Find("Goal").GetComponent<Transform>();
        rb = GetComponent<Rigidbody>();
    }
    void Update()
    {
        if(state == State.LeftCliff)
        {
            transform.LookAt(flower);
            if(transform.position.x < -5.5f)
            {
                transform.position += new Vector3(0.05f, 0, 0);
            }
            if(Vector3.Distance(transform.position, flower.position) < 3f)
            {
                JumpTo(flower.position);
                state = State.Jumping;
            }
        }
        else if(state == State.OnFlower)
        {
            transform.LookAt(goal);

            if(Vector3.Distance(transform.position, goal.position) < 5f)
            {
                transform.SetParent(null);
                rb.isKinematic = false;
                JumpTo(goal.position);
                state = State.Jumping;
            }
        }
        else if(state == State.RightCliff)
        {
            transform.position += transform.forward * 0.1f;
        }
    }

    void JumpTo(Vector3 target)
    {
        Vector3 dir = (target - transform.position).normalized;
        rb.AddForce(dir * 2f + Vector3.up * 5f, ForceMode.Impulse);
    }

    void OnCollisionEnter(Collision col)
    {
        if(col.gameObject.name == "LeftCliff")
        {
            state = State.LeftCliff;
        }
        if(col.gameObject.name == "Flower")
        {
            state = State.OnFlower;
            transform.SetParent(flower);
            rb.isKinematic = true;
        }
        if(col.gameObject.name == "RightCliff")
        {
            state = State.RightCliff;
        }
        
    }
}
