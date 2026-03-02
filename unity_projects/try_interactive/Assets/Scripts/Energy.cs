using System.Collections;
using System.Collections.Generic;
using UnityEngine;

public class Energy : MonoBehaviour
{
    public DropGameController drop;
    // Start is called before the first frame update
    void Start()
    {
        drop = GameObject.Find("Root").GetComponent<DropGameController>();
    }

    // Update is called once per frame
    void Update()
    {
        if (transform.position.y < -10)
        {
            Destroy(this.gameObject);
        }
    }

    void OnTriggerEnter(Collider col)
    {
        if(col.gameObject.tag == "Plant")
        {
            drop.score ++;
            Destroy(this.gameObject);
        }
    }
}
