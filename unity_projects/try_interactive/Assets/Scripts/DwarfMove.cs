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
    private float winTime;

    enum State
    {
        LeftCliff,
        OnFlower,
        RightCliff,
        Jumping,
        Running,
        Fallen
    }

    [SerializeField] private State state = State.Running;

    void Start()
    {
        flower = GameObject.Find("Flower").GetComponent<Transform>();
        goal = GameObject.Find("Goal").GetComponent<Transform>();
        rb = GetComponent<Rigidbody>();
        anim = GetComponent<Animator>();
        winTime = 0;
    }
    void Update()
    {
        if(state == State.Running)
        {
            anim.SetTrigger("run");
            transform.rotation = Quaternion.EulerAngles(0,90,0); 
            if(transform.position.x < -5.5f || transform.position.x > 5f)
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
            transform.rotation = Quaternion.EulerAngles(0,180,0); 
            anim.SetTrigger("win");
            winTime += Time.deltaTime;
            if(winTime > 1.0f)
            {
                winTime = 0;
                state = State.Running;    
            }
        }
        else if(state == State.Jumping)
        {
            anim.SetTrigger("jump");
        }
        else if(state == State.Fallen)
        {
            anim.SetTrigger("fall");
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
        if(col.gameObject.name == "Ground")
        {
            state = State.Fallen;
        }
        
    }

}
