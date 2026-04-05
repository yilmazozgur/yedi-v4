using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UI;

public class SuperDisplay : MonoBehaviour
{
    public float baseSuper = 3;
    Text superText;
    public float superCount;
    float superCountRounded;
    ParticleSystem particleVFX;


    void Start()
    {
        superText = GetComponent<Text>();
        particleVFX = GetComponentInChildren<ParticleSystem>();
        superCount = baseSuper;
        UpdateDisplay();
    }

    public bool HaveEnoughSuper(float amount)
    {
        return superCount >= amount;
    }

    public void SpendSuper(float cost)
    {
        superCount -= cost;
        superCount = Mathf.Max(superCount, 0f);
        UpdateDisplay();
    }

    private void UpdateDisplay()
    {
        superCountRounded = Mathf.Round(superCount);
        superText.text = superCountRounded.ToString() + " Super";
    }

    public void PlayAnimation()
    {
        particleVFX.Play();
    }

}
