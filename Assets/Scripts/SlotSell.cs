using System.Collections;
using System.Collections.Generic;
using UnityEngine;

public class SlotSell : MonoBehaviour
{
    ParticleSystem particleVFX;
    AudioSource audioCardSell;
    // Start is called before the first frame update
    void Start()
    {
        particleVFX = GetComponentInChildren<ParticleSystem>();
        audioCardSell = GetComponentInChildren<AudioSource>();
    }

    public void SellEffectInitiate()
    {
        if (particleVFX)
        {
            particleVFX.Play();
            audioCardSell.Play();
        }
        
    }


}
