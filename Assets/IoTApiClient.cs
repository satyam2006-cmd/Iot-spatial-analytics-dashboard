using System;
using System.Collections;
using TMPro;
using UnityEngine;
using UnityEngine.Networking;

public class IoTApiClient : MonoBehaviour
{
    [Header("API Settings")]
    public string apiUrl =
        "http://127.0.0.1:8000/api/readings/latest";

    public float refreshInterval = 2f;

    [Header("Existing UI")]
    public TMP_Text sensorDataText;

    [Header("AR Dashboard UI")]
    public TMP_Text adcValueText;
    public TMP_Text connectionStatusText;
    public TMP_Text lastUpdatedText;

    public ADCGauge adcGauge;

    [Header("Sensor Status")]
public TMP_Text sensorStatusText;

[Header("3D Digital Twin")]
public SensorReactiveObject reactiveObject;

public int demoThreshold = 350;


    [Serializable]
    public class SensorReading
    {
        public int id;
        public string device;
        public string sensor;
        public int sequence;
        public long uptime_ms;
        public int mq135_adc;
        public string collected_at;
    }

    [Serializable]
    public class ApiResponse
    {
        public SensorReading reading;
    }

    private void Start()
    {
        StartCoroutine(PollSensorData());
    }

    private IEnumerator PollSensorData()
    {
        while (true)
        {
            yield return FetchLatestReading();
            yield return new WaitForSeconds(refreshInterval);
        }
    }

    private IEnumerator FetchLatestReading()
    {
        using (UnityWebRequest request =
               UnityWebRequest.Get(apiUrl))
        {
            request.timeout = 5;
            yield return request.SendWebRequest();

            if (request.result !=
                UnityWebRequest.Result.Success)
            {
                string errorText = "Connection: Disconnected";

                Debug.LogError(
                    "API connection failed: " + request.error
                );

                UpdateText(sensorDataText,
                    "API connection failed\n" + request.error);

                UpdateText(connectionStatusText, errorText);

                yield break;
            }

            string json = request.downloadHandler.text;
            Debug.Log("API response: " + json);

            ApiResponse response = null;

            try
            {
                response = JsonUtility.FromJson<ApiResponse>(json);
            }
            catch (Exception e)
            {
                Debug.LogError("JSON parsing error: " + e.Message);
            }

            if (response == null || response.reading == null)
            {
                UpdateText(connectionStatusText,
                    "Connection: Data error");

                Debug.LogError("API response has no reading object.");
                yield break;
            }

            SensorReading reading = response.reading;

            if (adcGauge != null)
                {
                    adcGauge.SetADC(reading.mq135_adc);
                }

                if (sensorStatusText != null)
                    {
                        if (reading.mq135_adc >= demoThreshold)
                        {
                            sensorStatusText.text =
                                "Sensor Status: ABOVE DEMO THRESHOLD";
                            sensorStatusText.color = Color.red;
                        }
                        else
                        {
                            sensorStatusText.text =
                                "Sensor Status: NORMAL RANGE";
                            sensorStatusText.color = Color.green;
                        }
                    }

                    if (reactiveObject != null)
                            {
                                reactiveObject.SetADC(reading.mq135_adc);
                            }
            string updatedAt = DateTime.Now.ToString("HH:mm:ss");

            string display =
                "IOT DIGITAL TWIN\n" +
                "Sensor: " + reading.sensor + "\n" +
                "ADC: " + reading.mq135_adc + "\n" +
                "Sequence: " + reading.sequence + "\n" +
                "Connection: Connected\n" +
                "Updated: " + updatedAt;

            UpdateText(sensorDataText, display);

            UpdateText(adcValueText,
                "ADC: " + reading.mq135_adc);

            UpdateText(connectionStatusText,
                "Connection: Connected");

            UpdateText(lastUpdatedText,
                "Last updated: " + updatedAt);

            Debug.Log("MQ-135 ADC: " + reading.mq135_adc);
        }
    }

    private void UpdateText(TMP_Text target, string value)
    {
        if (target != null)
            target.text = value;
    }
}