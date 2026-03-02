using System.Collections;
using System.Collections.Generic;
using UnityEngine;

public class DropGameController : MonoBehaviour
{
    [SerializeField] private float delayTime;
    [SerializeField] private Vector3 dropArea;
    private float timeCount;
    [SerializeField] private GameObject obj;
    public int score;

    // Start is called before the first frame update
    void Start()
    {
        score = 0;
    }

    // Update is called once per frame
    void Update()
    {
        if (timeCount > delayTime)
        {
            timeCount = 0;
            float x = Random.Range(-dropArea.x, dropArea.x);
            float z = Random.Range(-dropArea.z, dropArea.z);
            float y = dropArea.y;
            Instantiate(obj, new Vector3(x,y,z), Quaternion.identity);
        }
        timeCount += Time.deltaTime;
    }
}
