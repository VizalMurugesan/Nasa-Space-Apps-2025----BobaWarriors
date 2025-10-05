using System;
using System.Net.Sockets;
using System.Text;
using UnityEngine;

public class PythonUnityConnector : MonoBehaviour
{
    TcpClient client;
    NetworkStream stream;

    [Header("Numbers to send to Python")]
    public int numberA = 5;
    public int numberB = 7;

    void Start()
    {
        try
        {
            client = new TcpClient("127.0.0.1", 5005); // Make sure Python uses the same port
            stream = client.GetStream();
            Debug.Log("Connected to Python server!");
        }
        catch (Exception e)
        {
            Debug.LogError("Socket error: " + e);
        }
    }

    void Update()
    {
        // Press Space to send numbers
        if (Input.GetKeyDown(KeyCode.Space))
        {
            SendNumbers(numberA, numberB);
        }
    }

    void SendNumbers(int a, int b)
    {
        if (client == null || stream == null)
        {
            Debug.LogError("Not connected to Python!");
            return;
        }

        try
        {
            // Send numbers as "a,b"
            string message = a + "," + b;
            byte[] data = Encoding.UTF8.GetBytes(message);
            stream.Write(data, 0, data.Length);

            // Receive response
            byte[] buffer = new byte[1024];
            int bytesRead = stream.Read(buffer, 0, buffer.Length);
            string response = Encoding.UTF8.GetString(buffer, 0, bytesRead);

            Debug.Log($"Python returned: {response}");
        }
        catch (Exception e)
        {
            Debug.LogError("Error sending/receiving data: " + e);
        }
    }

    void OnApplicationQuit()
    {
        stream?.Close();
        client?.Close();
        Debug.Log("Closed connection to Python server.");
    }
}



