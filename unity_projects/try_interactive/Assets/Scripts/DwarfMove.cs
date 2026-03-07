using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.AI;

public class DwarfMove : MonoBehaviour
{
    private Transform flower;
    private Transform goal;
    private Rigidbody rb;
    private Animator anim;

    enum State
    {
        LeftCliff,
        OnFlower,
        RightCliff,
        Jumping,
        Running
        
    }

    private State state = State.Running;

    void Start()
    {
        flower = GameObject.Find("Flower").GetComponent<Transform>();
        goal = GameObject.Find("Goal").GetComponent<Transform>();
        rb = GetComponent<Rigidbody>();
        anim = GetComponent<Animator>();
    }
    void Update()
    {
        if(state == State.Running)
        {
            anim.SetTrigger("run");
            if(transform.position.x < -5.5f)
            {
                transform.position += new Vector3(0.05f, 0, 0);
            }
            else
            {
                state = State.LeftCliff;
            }
            
        }
        else if(state == State.LeftCliff)
        {
            transform.LookAt(flower);
            anim.SetTrigger("idle");
            if(Vector3.Distance(transform.position, flower.position) < 3f)
            {
                JumpTo(flower.position);
                state = State.Jumping;
            }
        }
        else if(state == State.OnFlower)
        {
            transform.LookAt(goal);
            anim.SetTrigger("idle");
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
            anim.SetTrigger("win");
        }
        else if(state == State.Jumping)
        {
            anim.SetTrigger("jump");
        }
        else if(state == State.Running)
        {
            anim.SetTrigger("run");
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
            state = State.Running;
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

    //勝利コルーチン
}
