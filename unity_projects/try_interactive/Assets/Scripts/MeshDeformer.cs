using UnityEngine;

[RequireComponent(typeof(MeshFilter))]
public class MeshDeformer : MonoBehaviour
{
    public float moveSpeed = 0.3f;
    public float deformRadius = 0.3f;
    public float deformStrength = 0.3f;
    public float timePeriod = 0.3f;

    private Mesh mesh;
    private Vector3[] baseVertices;
    private Vector3[] deformedVertices;

    void Start()
    {
        mesh = GetComponent<MeshFilter>().mesh;
        baseVertices = mesh.vertices;
        deformedVertices = new Vector3[baseVertices.Length];
    }

    void Update()
    {
        Vector2 input = new Vector2(Input.GetAxis("Horizontal"), Input.GetAxis("Vertical"));
        Vector2 center = new Vector2(input.x, input.y) * moveSpeed;

        for (int i = 0; i < baseVertices.Length; i++)
        {
            Vector3 v = baseVertices[i];
            Vector2 pos2D = new Vector2(v.x, v.z); 
            float dist = Vector2.Distance(pos2D, center);

            float height = Mathf.Exp(-dist * dist / (deformRadius * deformRadius))*Mathf.Sin(-dist*2*Mathf.PI/deformRadius + Time.time/timePeriod) * deformStrength;

            deformedVertices[i] = new Vector3(v.x, height, v.z); // ← ここを修正
        }

        mesh.vertices = deformedVertices;
        mesh.RecalculateNormals();
    }
}
