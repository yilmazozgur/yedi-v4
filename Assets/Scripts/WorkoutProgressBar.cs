using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using Michsky.UI.ModernUIPack; // namespace
using UnityEngine.UI;

public class WorkoutProgressBar : MonoBehaviour
{
    //[SerializeField] ProgressBar workoutProgress;
    Text workoutProgress; // Your pb variable

    // Start is called before the first frame update
    void Start()
    {
        workoutProgress = GetComponent<Text>();
    }

    public void AdjustSlider(float percent, bool justInitialized)
    {
        if(percent > 0f)
        {
            workoutProgress.text = "% " + percent.ToString();
        }
        else
        {
            StartCoroutine(AnimateHundredPercent(percent, justInitialized));
        }
    }

    IEnumerator AnimateHundredPercent(float percent, bool justInitialized)
    {
        if(justInitialized == true)
        {
            Color original = workoutProgress.color;
            workoutProgress.color = Color.red;
            workoutProgress.text = "% 100";
            yield return new WaitForSeconds(0.5f);
            workoutProgress.color = original;
        }
        workoutProgress.text = "% 0";
    }

}
