using System;
using System.Net.Sockets;
using System.Text;
using UnityEditor.MemoryProfiler;
using UnityEngine;

public class PythonUnityConnection : MonoBehaviour
{
    TcpClient client;
    NetworkStream stream;
    // Start is called once before the first execution of Update after the MonoBehaviour is created
    void Start()
    {
        //var client = new TcpClient("127.0.0.1", 5005);
        //var stream = client.GetStream();

        //byte[] data = Encoding.UTF8.GetBytes("5,7");
        //stream.Write(data, 0, data.Length);

        //byte[] buffer = new byte[1024];
        //int bytesRead = stream.Read(buffer, 0, buffer.Length);

        // Debug.Log("Result: " + Encoding.UTF8.GetString(buffer, 0, bytesRead));

        // stream.Close();
        //client.Close();
        try
        {
            client = new TcpClient("127.0.0.1", 5005);
            stream = client.GetStream();
            Debug.Log("Connected to Python server!");
        }
        catch (Exception e)
        {
            Debug.Log("Socket error: " + e);
        }
    }

    // Call this function from anywhere in Unity
    public int SendNumbers(int a, int b)
    {
        if (client == null || stream == null)
        {
            Debug.LogError("Not connected to Python!");
            return -1;
        }

        // Send numbers
        string message = a + "," + b;
        byte[] data = Encoding.UTF8.GetBytes(message);
        stream.Write(data, 0, data.Length);

        // Receive response
        byte[] buffer = new byte[1024];
        int bytesRead = stream.Read(buffer, 0, buffer.Length);
        string response = Encoding.UTF8.GetString(buffer, 0, bytesRead);

        Debug.Log("Result from Python: " + response);

        int result;
        if (int.TryParse(response, out result))
            return result;
        else
            return -1;
    }

    void OnApplicationQuit()
    {
        stream?.Close();
        client?.Close();
    }
    // Update is called once per frame
    void Update()
    {
        if (Input.GetKeyDown(KeyCode.Space))
        {
            //int sum = connection.SendNumbers(3, 9);
            //Debug.Log("The sum is: " + sum);
        }
    }

}
