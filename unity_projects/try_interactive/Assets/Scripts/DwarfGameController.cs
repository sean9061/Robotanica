using System.Collections;
using System.Collections.Generic;
using UnityEngine;

public class DwarfGameController : MonoBehaviour
{
    public float repeatSpan = 5f;
    public GameObject dwarfPref;
    public Vector3 summonPos;
    MeshRenderer flowerRend;
    // Start is called before the first frame update
    void Start()
    {
        Application.targetFrameRate = 24;   //フレームレートを24fpsに
        flowerRend = GameObject.Find("Flower").GetComponent<MeshRenderer>();
        InvokeRepeating("SummonDwarf", 0f, repeatSpan);
    }

    // Update is called once per frame
    void Update()
    {
        // VキーでFlower表示/非表示
        if (Input.GetKeyDown(KeyCode.V))
        {
            flowerRend.enabled = !flowerRend.enabled;
        }
    }

    void SummonDwarf()
    {
        float z = Random.Range(-2,2);
        Instantiate(dwarfPref, summonPos + new Vector3(0,0,z), Quaternion.identity);
    }
}
