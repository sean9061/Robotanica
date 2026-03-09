using UnityEngine;

public class RangeCubeController : MonoBehaviour
{
    public FlowerMove flower;

    void Update()
    {
        // 範囲サイズ
        transform.localScale =
            flower.moveRange * 2;
    }
}