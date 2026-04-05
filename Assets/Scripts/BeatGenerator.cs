using System.Collections;
using System.Collections.Generic;
using UnityEngine;

public class BeatGenerator : MonoBehaviour
{

    BeatSource beat1;
    BeatSource beat2;
    AudioSource beatSource1;
    AudioSource beatSource2;
    MusicPlayer musicPlayer;
    bool beatActivated = false;
    bool notInitialized = true;
    float beatTime = 0f;
    AudioClip audioClip1;
    AudioClip audioClip2;
    float timeStart = 0f;
    float beatPeriod = 1.8f;
    float beat2Delay = 0.28f;
    float beat2Period = 0.17f;
    string modeBeat;

    void Start()
    {
        musicPlayer = FindObjectOfType<MusicPlayer>();
        if (beatActivated == true)
        {
            if (musicPlayer != null)
            {
                musicPlayer.SetVolume(0f);
            }
        }

        BeatSource[] beats = FindObjectsOfType<BeatSource>();
        foreach (BeatSource beatIter in beats)
        {
            if (beatIter.gameObject.name == "Beat1")
            {
                beat1 = beatIter;
                beatSource1 = beat1.GetComponent<AudioSource>();
                audioClip1 = beatSource1.clip;
            }
            else
            {
                beat2 = beatIter;
                beatSource2 = beat2.GetComponent<AudioSource>();
                audioClip2 = beatSource2.clip;
            }
        }

        
    }

    IEnumerator PlayBeatUpdate()
    {
        Debug.Log("Beat Update Loop");
        beatSource1.Play();
        yield return new WaitForSeconds(1f);
        StartCoroutine(PlayBeat2Routine());
    }

    public void InitializeBeat(string modeBeatInput)
    {
        modeBeat = modeBeatInput;

        if (beatActivated == false)
        {
            return;
        }
       
        if (musicPlayer != null)
        {
            musicPlayer.SetVolume(0f);
        }

        if (notInitialized)
        {
            if(modeBeat == "double")
            {
                timeStart = Time.time;
                InvokeRepeating("PlayBeat1", 0.001f, beatPeriod);
                InvokeRepeating("PlayBeat2", beat2Delay * beatPeriod, beatPeriod);
                InvokeRepeating("PlayBeat2", (beat2Delay + beat2Period) * beatPeriod, beatPeriod);
                InvokeRepeating("PlayBeat2", (beat2Delay + 2f * beat2Period) * beatPeriod, beatPeriod);
                InvokeRepeating("PlayBeat2", (beat2Delay + 3f * beat2Period) * beatPeriod, beatPeriod);
                notInitialized = false;
            }
            else if (modeBeat == "double fast")
            {
                timeStart = Time.time;
                beatPeriod = beatPeriod / 1.3f;
                InvokeRepeating("PlayBeat1", 0.001f, beatPeriod);
                InvokeRepeating("PlayBeat2", beat2Delay * beatPeriod, beatPeriod);
                InvokeRepeating("PlayBeat2", (beat2Delay + beat2Period) * beatPeriod, beatPeriod);
                InvokeRepeating("PlayBeat2", (beat2Delay + 2f * beat2Period) * beatPeriod, beatPeriod);
                InvokeRepeating("PlayBeat2", (beat2Delay + 3f * beat2Period) * beatPeriod, beatPeriod);
                notInitialized = false;
            }
            else if(modeBeat == "single")
            {
                timeStart = Time.time;
                InvokeRepeating("PlayBeat1", 0.001f, beatPeriod);
                notInitialized = false;
            }
            else if (modeBeat == "single fast")
            {
                beatPeriod = beatPeriod / 1.6f;
                timeStart = Time.time;
                InvokeRepeating("PlayBeat1", 0.001f, beatPeriod);
                notInitialized = false;
            }
            else if (modeBeat == "tiktok")
            {
                timeStart = Time.time;
                InvokeRepeating("PlayBeat1", 0.001f, beatPeriod);
                InvokeRepeating("PlayBeat2", beat2Delay * beatPeriod, beatPeriod);
                notInitialized = false;
            }
            else if (modeBeat == "five")
            {
                beatPeriod = beatPeriod * 2.4f;
                //beat2Delay = beat2Delay * 1.5f;
                beat2Period = beat2Period * 1f;
                timeStart = Time.time;
                InvokeRepeating("PlayBeat1", 0.001f, beatPeriod);
                InvokeRepeating("PlayBeat2", beat2Delay * beatPeriod, beatPeriod);
                InvokeRepeating("PlayBeat2", (beat2Delay + beat2Period) * beatPeriod, beatPeriod);
                InvokeRepeating("PlayBeat2", (beat2Delay + 2f * beat2Period) * beatPeriod, beatPeriod);
                InvokeRepeating("PlayBeat2", (beat2Delay + 3f * beat2Period) * beatPeriod, beatPeriod);
                InvokeRepeating("PlayBeat2", (beat2Delay + 4f * beat2Period) * beatPeriod, beatPeriod);
                notInitialized = false;
            }

        }
    }

    public void StopBeat()
    {
        CancelInvoke();
    }

    void PlayBeat1()
    {
        beatSource1.Play();
    }

    public float GetBeat1Time(int beatNumber = 1)
    {
        //It has a different beat task. First beat is the warning.
        if (modeBeat == "five")
        {
            timeStart += 0.001f + beat2Delay * beatPeriod;
        }

        if (beatNumber ==1)
        {
            beatTime = (Time.time - timeStart) / beatPeriod;
            beatTime = beatTime - Mathf.Floor(beatTime);
        }
        else if (beatNumber == 2)
        {
            beatTime = (Time.time - timeStart - beat2Delay * beatPeriod) / beatPeriod;
            beatTime = beatTime - Mathf.Floor(beatTime);
        }
        else if (beatNumber == 3)
        {
            beatTime = (Time.time - timeStart - (beat2Delay + beat2Period) * beatPeriod) / beatPeriod;
            beatTime = beatTime - Mathf.Floor(beatTime);
        }
        else if (beatNumber == 4)
        {
            beatTime = (Time.time - timeStart - (beat2Delay + 2f * beat2Period) * beatPeriod) / beatPeriod;
            beatTime = beatTime - Mathf.Floor(beatTime);
        }
        else if (beatNumber == 5)
        {
            beatTime = (Time.time - timeStart - (beat2Delay + 3f * beat2Period) * beatPeriod) / beatPeriod;
            beatTime = beatTime - Mathf.Floor(beatTime);
        }

        return beatTime;
    }

    void PlayBeat2()
    {
        beatSource2.Play();
    }

    IEnumerator PlayBeat2Routine()
    {
        beatSource2.Play();
        yield return new WaitForSeconds(0.2f);
        beatSource2.Play();
    }

    public void SetBeatActivated(bool activationValue, string modeBeatInput = "double")
    {
        beatActivated = activationValue;
        //modeBeat = modeBeatInput;
    }

    public bool GetBeatActivated()
    {
        return beatActivated;
    }


    private void OnDestroy()
    {
        if (beatActivated == true && musicPlayer != null)
        {
            musicPlayer.SetVolume(PlayerPrefsController.GetMasterVolume());
        }
    }
}
