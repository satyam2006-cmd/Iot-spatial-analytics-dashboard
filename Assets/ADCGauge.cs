using UnityEngine;
using UnityEngine.UI;

public class ADCGauge : MonoBehaviour
{
    [Header("Gauge References")]
    public RectTransform fillRect;
    public Image fillImage;

    [Header("ADC Range")]
    public float maximumADC = 1023f;

    [Header("Display")]
    public bool useColorIndicator = true;

    private float maximumWidth;
    private bool initialized;

    private void Start()
    {
        InitializeGauge();
    }

    private void InitializeGauge()
    {
        if (fillRect == null)
        {
            Debug.LogError("ADCGauge: Assign GaugeFill RectTransform.");
            return;
        }

        maximumWidth = fillRect.parent
            .GetComponent<RectTransform>().rect.width;

        if (maximumWidth <= 0f)
        {
            Debug.LogError("ADCGauge: Background width must be greater than zero.");
            return;
        }

        fillRect.anchorMin = new Vector2(0f, 0.5f);
        fillRect.anchorMax = new Vector2(0f, 0.5f);
        fillRect.pivot = new Vector2(0f, 0.5f);
        fillRect.anchoredPosition = Vector2.zero;

        initialized = true;
        SetADC(0);
    }

    public void SetADC(int adcValue)
    {
        if (!initialized || fillRect == null)
            return;

        float normalized = Mathf.Clamp01(
            adcValue / maximumADC
        );

        fillRect.SetSizeWithCurrentAnchors(
            RectTransform.Axis.Horizontal,
            maximumWidth * normalized
        );

        if (useColorIndicator && fillImage != null)
        {
            if (normalized < 0.33f)
                fillImage.color = Color.green;
            else if (normalized < 0.66f)
                fillImage.color = Color.yellow;
            else
                fillImage.color = Color.red;
        }

        Debug.Log(
            "ADC Gauge updated: " + adcValue +
            " | Fill: " + (normalized * 100f).ToString("F1") + "%"
        );
    }
}