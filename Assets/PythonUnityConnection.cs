using System;
using System.Net.Sockets;
using System.Text;
using UnityEngine;

public class PythonUnityConnector : MonoBehaviour
{
    TcpClient client;
    NetworkStream stream;

    //Initializing variables that are going to be sent to python
    public string date, typeOfFertilizer, typeOfIrrigation, crop;

    void Start()
    {
        try
        {
            client = new TcpClient("127.0.0.1", 5005);
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
            SendVariables(date, typeOfFertilizer, typeOfIrrigation, crop);
        }
    }

    void SendVariables(string date, string fert, string iri, string crop)
    {
        if (client == null || stream == null)
        {
            Debug.LogError("Not connected to Python!");
            return;
        }

        try
        {
            // Send variables as one string, separated by commas
            string message = date + "," + fert + "," + iri + "," + crop;
            byte[] data = Encoding.UTF8.GetBytes(message);
            stream.Write(data, 0, data.Length);

            // Receive response
            byte[] buffer = new byte[1024];
            int bytesRead = stream.Read(buffer, 0, buffer.Length);
            string response = Encoding.UTF8.GetString(buffer, 0, bytesRead);

            /** Needs to be outputted in the right places
             *  date - no need to be returned,
             *  fert - no need to be returned,
             *  iri - no need to be returned.
             *  Unless it is needed for the outcome messages **/
            //Debug.Log($"Python returned: {response}");
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