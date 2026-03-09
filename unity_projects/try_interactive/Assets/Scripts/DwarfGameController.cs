using System.Collections;
using System.Collections.Generic;
using UnityEngine;

public class DwarfGameController : MonoBehaviour
{
    public float repeatSpan = 5f;
    public GameObject dwarfPref;
    public Vector3 summonPos;
    MeshRenderer flowerRend;
    MeshRenderer rangeRend;
    bool visible;
    // Start is called before the first frame update
    void Start()
    {
        Application.targetFrameRate = 24;   //フレームレートを24fpsに
        InvokeRepeating("SummonDwarf", 0f, repeatSpan);
        flowerRend = GameObject.Find("Flower").GetComponent<MeshRenderer>();
        rangeRend = GameObject.Find("RangeVisualizer").GetComponent<MeshRenderer>();
        visible = false;
        flowerRend.enabled = visible;
        rangeRend.enabled = visible;
    }

    void Update()
    {
        if (Input.GetKeyDown(KeyCode.Tab))
        {
            visible = !visible;
            flowerRend.enabled = visible;
            rangeRend.enabled = visible;
        }
    }
    void SummonDwarf()
    {
        float z = Random.Range(-2,2);
        Instantiate(dwarfPref, summonPos + new Vector3(0,0,z), Quaternion.identity);
    }
}
