using System.Collections;
using System.Collections.Generic;
using UnityEngine;

public class DwarfGameController : MonoBehaviour
{
    public float repeatSpan = 5f;
    public GameObject dwarfPref;
    public Vector3 summonPos;
    // Start is called before the first frame update
    void Start()
    {
        InvokeRepeating("SummonDwarf", 0f, repeatSpan);
    }

    // Update is called once per frame
    void Update()
    {
        
    }

    void SummonDwarf()
    {
        float z = Random.Range(-2,2);
        Instantiate(dwarfPref, summonPos + new Vector3(0,0,z), Quaternion.identity);
    }
}
