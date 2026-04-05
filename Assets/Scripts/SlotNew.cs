using System.Collections;
using System.Collections.Generic;
using UnityEngine;

public class SlotNew : MonoBehaviour
{
    ParticleSystem particleVFX;
    AudioSource audioCardDraw;
    // Start is called before the first frame update
    void Start()
    {
        particleVFX = GetComponentInChildren<ParticleSystem>();
        audioCardDraw = GetComponentInChildren<AudioSource>();
    }

    public void DrawEffectInitiate()
    {
        if (particleVFX)
        {
            particleVFX.Play();
            audioCardDraw.Play();
        }

    }

}
