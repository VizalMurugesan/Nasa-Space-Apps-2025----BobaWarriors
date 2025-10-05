using UnityEngine;

public class AudioManager : MonoBehaviour
{
    public AudioClip rainyClip;
    public AudioClip sunnyClip;
  
    public AudioClip windyClip;
    public AudioClip snowyClip;

    private AudioSource audioSource;

    void Awake()
    {
        // Automatically add an AudioSource component if not present
        audioSource = gameObject.AddComponent<AudioSource>();
        audioSource.loop = true;
    }

    public void PlayWeatherSound(TimeManager.Weather weather)
    {
        AudioClip clipToPlay = null;

        switch (weather)
        {
            case TimeManager.Weather.Rainy:
                clipToPlay = rainyClip;
                break;
            case TimeManager.Weather.Sunny:
                clipToPlay = sunnyClip;
                break;
            case TimeManager.Weather.Windy:
                clipToPlay = windyClip;
                break;
            case TimeManager.Weather.snowy:
                clipToPlay = snowyClip;
                break;
        }

        if (clipToPlay != null && audioSource.clip != clipToPlay)
        {
            audioSource.clip = clipToPlay;
            audioSource.Play();
        }
    }
}
