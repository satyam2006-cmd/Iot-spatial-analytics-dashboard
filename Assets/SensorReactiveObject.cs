using UnityEngine;

public class SensorReactiveObject : MonoBehaviour
{
    [Header("3D Object")]
    public Renderer targetRenderer;

    [Header("Demonstration Threshold")]
    public int demoThreshold = 350;

    [Header("Object Colors")]
    public Color normalColor = Color.green;
    public Color alertColor = Color.red;

    private MaterialPropertyBlock propertyBlock;
    private static readonly int BaseColorId =
        Shader.PropertyToID("_BaseColor");
    private static readonly int ColorId =
        Shader.PropertyToID("_Color");

    private void Awake()
    {
        propertyBlock = new MaterialPropertyBlock();

        if (targetRenderer == null)
        {
            targetRenderer = GetComponent<Renderer>();
        }
    }

    public void SetADC(int adcValue)
    {
        if (targetRenderer == null)
        {
            Debug.LogWarning(
                "SensorReactiveObject: Renderer is not assigned."
            );
            return;
        }

        Color selectedColor =
            adcValue >= demoThreshold ? alertColor : normalColor;

        targetRenderer.GetPropertyBlock(propertyBlock);
        propertyBlock.SetColor(BaseColorId, selectedColor);
        propertyBlock.SetColor(ColorId, selectedColor);
        targetRenderer.SetPropertyBlock(propertyBlock);

        Debug.Log(
            "3D object updated. ADC: " + adcValue +
            " | Color: " +
            (adcValue >= demoThreshold ? "RED" : "GREEN")
        );
    }
}