using System;
using System.IO;
using System.Net.Sockets;
using System.Text;
using UnityEngine;

public class PythonUnityConnector : MonoBehaviour
{
    [Header("Python Connection")]
    public string host = "127.0.0.1";
    public int port = 5005;
    public int readTimeoutMs = 0;

    [Header("Simulation Inputs")]
    public string date;
    public string typeOfFertilizer;
    public string typeOfIrrigation;
    public string crop;
    public float latitude = 49.104f;
    public float longitude = -122.66f;
    public float elevation = 36f;


    [Header("Manual Actions (units)")]
    public float irrigationAmountCm = 2f;
    [Range(0f, 1f)]
    public float irrigationEfficiency = 0.75f;
    public float fertilizerAmountKgHa = 40f;
    [Range(0f, 1f)]
    public float fertilizerNh4Fraction = 0.7f;

    private TcpClient client;
    private NetworkStream stream;
    private readonly byte[] readBuffer = new byte[4096];
    private bool isInitialized;
    private int tickCounter;
    private SimulationInitRequest lastInitRequest;

    private void Start()
    {
        EnsureConnected();
    }

    private void Update()
    {
        if (Input.GetKeyDown(KeyCode.RightArrow))
        {
            if (!isInitialized)
            {
                if (InitializeSimulation())
                {
                    RequestNextTick();
                }
            }
            else
            {
                RequestNextTick();
            }
        }

        if (Input.GetKeyDown(KeyCode.Space))
        {
            InitializeSimulation(forceReset: true);
        }

        if (Input.GetKeyDown(KeyCode.W))
        {
            RequestWater(irrigationAmountCm, irrigationEfficiency);
        }

        if (Input.GetKeyDown(KeyCode.F))
        {
            RequestFertilizer(fertilizerAmountKgHa, fertilizerNh4Fraction);
        }
    }

    private bool EnsureConnected()
    {
        if (client != null && client.Connected && stream != null)
        {
            return true;
        }

        try
        {
            stream?.Dispose();
            client?.Close();

            client = new TcpClient();
            int resolvedTimeout = readTimeoutMs > 0 ? readTimeoutMs : System.Threading.Timeout.Infinite;
            client.ReceiveTimeout = resolvedTimeout;
            client.SendTimeout = resolvedTimeout;
            client.Connect(host, port);
            stream = client.GetStream();
            if (stream.CanTimeout)
            {
                stream.ReadTimeout = resolvedTimeout;
                stream.WriteTimeout = resolvedTimeout;
            }

            string handshake = TryReadLineWithTimeout(3000);
            if (!string.IsNullOrEmpty(handshake))
            {
                Debug.Log($"Python handshake: {handshake}");
            }

            Debug.Log($"Connected to Python server at {host}:{port}");
            isInitialized = false;
            tickCounter = 0;
            lastInitRequest = null;
            return true;
        }
        catch (Exception e)
        {
            Debug.LogError($"Socket error when connecting to Python server: {e.Message}");
            stream = null;
            client = null;
            return false;
        }
    }

    private bool InitializeSimulation(bool forceReset = false)
    {
        if (!EnsureConnected())
        {
            Debug.LogError("Cannot initialize because Python server is unavailable.");
            return false;
        }

        if (isInitialized && !forceReset)
        {
            return true;
        }

        var initRequest = new SimulationInitRequest
        {
            action = "init",
            date = string.IsNullOrWhiteSpace(date) ? DateTime.UtcNow.ToString("yyyy-MM-dd") : date,
            fertilizer = string.IsNullOrWhiteSpace(typeOfFertilizer) ? "none" : typeOfFertilizer,
            irrigation = string.IsNullOrWhiteSpace(typeOfIrrigation) ? "none" : typeOfIrrigation,
            crop = string.IsNullOrWhiteSpace(crop) ? "wheat" : crop,
            lat = latitude,
            lon = longitude,
            elev = elevation,
        };

        var response = SendPayload(initRequest);
        if (response == null)
        {
            return false;
        }

        if (!response.ok)
        {
            Debug.LogError($"Python server error during init: {response.error}");
            return false;
        }

        if (response.result != null && !string.IsNullOrEmpty(response.result.message))
        {
            Debug.Log($"Python init: {response.result.message}");
        }
        else
        {
            Debug.Log("Python simulation initialized.");
        }

        isInitialized = true;
        tickCounter = 0;
        lastInitRequest = new SimulationInitRequest
        {
            action = initRequest.action,
            date = initRequest.date,
            fertilizer = initRequest.fertilizer,
            irrigation = initRequest.irrigation,
            crop = initRequest.crop,
            lat = initRequest.lat,
            lon = initRequest.lon,
            elev = initRequest.elev,
        };
        return true;
    }

    private void RequestNextTick(int steps = 1)
    {
        if (!EnsureConnected())
        {
            Debug.LogError("Cannot request tick because Python server is unavailable.");
            return;
        }

        if (!isInitialized)
        {
            if (!InitializeSimulation())
            {
                return;
            }
        }

        if (lastInitRequest == null)
        {
            Debug.LogError("Cannot request tick before a successful initialization.");
            return;
        }

        var request = new SimulationTickRequest
        {
            action = "tick",
            steps = Mathf.Max(1, steps),
            date = lastInitRequest.date,
            fertilizer = lastInitRequest.fertilizer,
            irrigation = lastInitRequest.irrigation,
            crop = lastInitRequest.crop,
            lat = lastInitRequest.lat,
            lon = lastInitRequest.lon,
            elev = lastInitRequest.elev,
        };

        var response = SendPayload(request);
        if (response == null)
        {
            return;
        }

        if (!response.ok)
        {
            Debug.LogError($"Python server error during tick: {response.error}");
            return;
        }

        if (response.result == null)
        {
            Debug.LogWarning("Python server returned success without a result payload.");
            return;
        }

        tickCounter = response.result.tick;
        var metrics = response.result.metrics;
        var weatherLog = BuildWeatherLog(response.result.weather);
        if (metrics != null)
        {
            var line = $"Tick {response.result.tick} (steps {response.result.steps}) on {response.result.day}: Soil Moisture {metrics.soil_moisture:F3}, Soil N {metrics.soil_n:F3}, Yield Rate {metrics.yield_rate:F2}";
            if (!string.IsNullOrEmpty(weatherLog))
            {
                line += $"\n{weatherLog}";
            }
            Debug.Log(line);
        }
        else
        {
            var line = $"Tick {response.result.tick} on {response.result.day} executed.";
            if (!string.IsNullOrEmpty(weatherLog))
            {
                line += $"\n{weatherLog}";
            }
            Debug.Log(line);
        }

        if (response.result.finished)
        {
            Debug.Log("Simulation has reached its termination flag.");
        }
    }

    public void RequestWater(float amountCm, float efficiency)
    {
        if (!EnsureConnected())
        {
            Debug.LogError("Cannot request watering because Python server is unavailable.");
            return;
        }

        if (!isInitialized && !InitializeSimulation())
        {
            return;
        }

        if (lastInitRequest == null)
        {
            Debug.LogError("Initialize the simulation before sending watering commands.");
            return;
        }

        var request = new SimulationWaterRequest
        {
            action = "water",
            amount_cm = Mathf.Max(0f, amountCm),
            efficiency = Mathf.Clamp01(efficiency),
            auto_steps = 1,
            date = lastInitRequest.date,
            fertilizer = lastInitRequest.fertilizer,
            irrigation = lastInitRequest.irrigation,
            crop = lastInitRequest.crop,
            lat = lastInitRequest.lat,
            lon = lastInitRequest.lon,
            elev = lastInitRequest.elev,
        };

        var response = SendPayload(request);
        if (response == null)
        {
            return;
        }

        if (!response.ok)
        {
            Debug.LogError($"Python server error during watering: {response.error}");
            return;
        }

        if (response.result == null)
        {
            Debug.LogWarning("Water command acknowledged without result payload.");
            return;
        }

        tickCounter = response.result.tick;
        var metrics = response.result.metrics;
        var weatherLog = BuildWeatherLog(response.result.weather);

        if (metrics != null)
        {
            var line = $"Water applied ({amountCm:F2} cm, eff {Mathf.Clamp01(efficiency):F2}). Soil Moisture {metrics.soil_moisture:F3}, Soil N {metrics.soil_n:F3}, Yield Rate {metrics.yield_rate:F2}";
            if (!string.IsNullOrEmpty(weatherLog))
            {
                line += $"\n{weatherLog}";
            }
            Debug.Log(line);
        }
        else if (!string.IsNullOrEmpty(weatherLog))
        {
            Debug.Log($"Water command acknowledged.\n{weatherLog}");
        }
    }




    public void RequestFertilizer(float amountKgHa, float nh4Fraction)
    {
        if (!EnsureConnected())
        {
            Debug.LogError("Cannot request fertilizing because Python server is unavailable.");
            return;
        }

        if (!isInitialized && !InitializeSimulation())
        {
            return;
        }

        if (lastInitRequest == null)
        {
            Debug.LogError("Initialize the simulation before sending fertilizing commands.");
            return;
        }

        var request = new SimulationFertilizerRequest
        {
            action = "fertilize",
            amount_kg_ha = Mathf.Max(0f, amountKgHa),
            nh4_fraction = Mathf.Clamp01(nh4Fraction),
            auto_steps = 1,
            date = lastInitRequest.date,
            fertilizer = lastInitRequest.fertilizer,
            irrigation = lastInitRequest.irrigation,
            crop = lastInitRequest.crop,
            lat = lastInitRequest.lat,
            lon = lastInitRequest.lon,
            elev = lastInitRequest.elev,
        };

        var response = SendPayload(request);
        if (response == null)
        {
            return;
        }

        if (!response.ok)
        {
            Debug.LogError($"Python server error during fertilizing: {response.error}");
            return;
        }

        if (response.result == null)
        {
            Debug.LogWarning("Fertilizer command acknowledged without result payload.");
            return;
        }

        tickCounter = response.result.tick;
        var metrics = response.result.metrics;
        var weatherLog = BuildWeatherLog(response.result.weather);

        if (metrics != null)
        {
            var line = $"Fertilizer applied ({amountKgHa:F1} kg/ha, NH4 {Mathf.Clamp01(nh4Fraction):F2}). Soil Moisture {metrics.soil_moisture:F3}, Soil N {metrics.soil_n:F3}, Yield Rate {metrics.yield_rate:F2}";
            if (!string.IsNullOrEmpty(weatherLog))
            {
                line += $"\n{weatherLog}";
            }
            Debug.Log(line);
        }
        else if (!string.IsNullOrEmpty(weatherLog))
        {
            Debug.Log($"Fertilizer command acknowledged.\n{weatherLog}");
        }
    }




    private CropSimulationResponse SendPayload(object payload)
    {
        if (stream == null)
        {
            Debug.LogError("Cannot send payload because stream is null.");
            return null;
        }

        string message = JsonUtility.ToJson(payload) + "\n";
        byte[] data = Encoding.UTF8.GetBytes(message);

        try
        {
            stream.Write(data, 0, data.Length);
        }
        catch (Exception e)
        {
            Debug.LogError($"Error writing to Python stream: {e.Message}");
            stream = null;
            return null;
        }

        for (int attempt = 0; attempt < 8; attempt++)
        {
            string responseJson = ReadLineFromStream();
            if (string.IsNullOrEmpty(responseJson))
            {
                Debug.LogWarning("Python server response was empty.");
                return null;
            }

            CropSimulationResponse response = null;
            try
            {
                response = JsonUtility.FromJson<CropSimulationResponse>(responseJson);
            }
            catch (Exception ex)
            {
                Debug.LogWarning($"Unable to parse python response ({ex.Message}): {responseJson}");
                continue;
            }

            if (response != null && response.result == null && string.IsNullOrEmpty(response.error) && !string.IsNullOrEmpty(response.message))
            {
                Debug.Log($"Python message: {response.message}");
                continue;
            }

            if (response == null)
            {
                Debug.LogWarning($"Unable to parse python response: {responseJson}");
                continue;
            }

            return response;
        }

        Debug.LogWarning("No valid response received from Python after multiple attempts.");
        return null;
    }

    private string TryReadLineWithTimeout(int timeoutMs)
    {
        if (stream == null)
        {
            return null;
        }

        var builder = new StringBuilder();
        int originalTimeout = 0;
        bool restoreTimeout = false;

        try
        {
            if (stream.CanTimeout && timeoutMs > 0)
            {
                originalTimeout = stream.ReadTimeout;
                stream.ReadTimeout = timeoutMs;
                restoreTimeout = true;
            }

            while (true)
            {
                int bytesRead = stream.Read(readBuffer, 0, readBuffer.Length);
                if (bytesRead == 0)
                {
                    break;
                }

                string segment = Encoding.UTF8.GetString(readBuffer, 0, bytesRead);
                int newlineIndex = segment.IndexOf('\n');
                if (newlineIndex >= 0)
                {
                    builder.Append(segment, 0, newlineIndex);
                    return builder.ToString().Trim();
                }

                builder.Append(segment);
            }
        }
        catch (IOException)
        {
            return builder.Length > 0 ? builder.ToString().Trim() : null;
        }
        catch (Exception e)
        {
            Debug.LogError($"Error reading from Python stream: {e.Message}");
            stream = null;
            return null;
        }
        finally
        {
            if (restoreTimeout && stream != null && stream.CanTimeout)
            {
                stream.ReadTimeout = originalTimeout;
            }
        }

        return builder.Length > 0 ? builder.ToString().Trim() : null;
    }


    private string FormatWeather(WeatherPayload weather)
    {
        if (weather == null)
        {
            return string.Empty;
        }

        string forecast = (weather.forecast != null && weather.forecast.Length > 0) ? string.Join("/", weather.forecast) : "none";
        string summary = string.IsNullOrEmpty(weather.current_summary) ? "n/a" : weather.current_summary;
        return $"Weather: {summary} | Forecast: {forecast}";
    }

    private string BuildWeatherLog(WeatherPayload weather)
    {
        if (weather == null)
        {
            return string.Empty;
        }

        var builder = new StringBuilder();
        string summary = FormatWeather(weather);
        if (!string.IsNullOrEmpty(summary))
        {
            builder.Append(summary);
        }

        if (!string.IsNullOrEmpty(weather.current_json))
        {
            if (builder.Length > 0)
            {
                builder.AppendLine();
            }
            builder.Append("Weather Data: ");
            builder.Append(weather.current_json);
        }

        return builder.ToString();
    }

    private string ReadLineFromStream()
    {
        if (stream == null)
        {
            return null;
        }

        var builder = new StringBuilder();
        try
        {
            while (true)
            {
                int bytesRead = stream.Read(readBuffer, 0, readBuffer.Length);
                if (bytesRead == 0)
                {
                    break;
                }

                string segment = Encoding.UTF8.GetString(readBuffer, 0, bytesRead);
                int newlineIndex = segment.IndexOf('\n');
                if (newlineIndex >= 0)
                {
                    builder.Append(segment, 0, newlineIndex);
                    return builder.ToString().Trim();
                }

                builder.Append(segment);
            }
        }
        catch (Exception e)
        {
            Debug.LogError($"Error reading from Python stream: {e.Message}");
            stream = null;
        }

        return builder.Length > 0 ? builder.ToString().Trim() : null;
    }

    private void OnApplicationQuit()
    {
        stream?.Close();
        client?.Close();
        Debug.Log("Closed connection to Python server.");
    }

    [Serializable]
    private class SimulationInitRequest
    {
        public string action;
        public string date;
        public string fertilizer;
        public string irrigation;
        public string crop;
        public float lat;
        public float lon;
        public float elev;
    }

    [Serializable]
    private class SimulationWaterRequest
    {
        public string action;
        public float amount_cm;
        public float efficiency;
        public int auto_steps;
        public string date;
        public string fertilizer;
        public string irrigation;
        public string crop;
        public float lat;
        public float lon;
        public float elev;
    }

    [Serializable]
    private class SimulationFertilizerRequest
    {
        public string action;
        public float amount_kg_ha;
        public float nh4_fraction;
        public int auto_steps;
        public string date;
        public string fertilizer;
        public string irrigation;
        public string crop;
        public float lat;
        public float lon;
        public float elev;
    }

    private class SimulationTickRequest
    {
        public string action;
        public int steps;
        public string date;
        public string fertilizer;
        public string irrigation;
        public string crop;
        public float lat;
        public float lon;
        public float elev;
    }

    [Serializable]
    private class WeatherPayload
    {
        public string current_summary;
        public string current_json;
        public string[] forecast;
    }

    [Serializable]
    private class CropSimulationResponse
    {
        public bool ok;
        public CropTickResult result;
        public string error;
        public string message;
    }

    [Serializable]
    private class CropTickResult
    {
        public string message;
        public int tick;
        public int steps;
        public string day;
        public CropTickMetrics metrics;
        public WeatherPayload weather;
        public CropSimulationState state;
        public bool finished;
    }

    [Serializable]
    private class CropTickMetrics
    {
        public float soil_moisture;
        public float soil_n;
        public float yield_rate;
    }

    [Serializable]
    private class CropSimulationState
    {
        public float DVS;
        public float LAI;
        public float SM;
        public float[] SM_profile;
        public float TAGP;
        public float TWSO;
        public float TRA;
        public float EVS;
        public float biomass;
        public float soil_n;
        public float yield_rate;
    }
}
