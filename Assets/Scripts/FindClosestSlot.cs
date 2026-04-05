using System.Collections;
using System.Collections.Generic;
using UnityEngine;

public class FindClosestSlot : MonoBehaviour
{
	SlotGeneric slotSelected;
	CardFrame cardFrame;
	bool isDragging;
	float distanceToSlot;
	float distanceToClosestSlot;
	SlotGeneric closestSlot;
	SlotGeneric[] allSlots;
	SlotSell slotSell;
	public float[] minDistanceSlots = new float[5] { 10000f, 10000f, 10000f, 10000f, 10000f };
	public float minDistanceAnchor = 10000f;
	float distanceToAnchor;
	int indexIter = 0;


	private void Start()
    {
		slotSell = FindObjectOfType<SlotSell>();
		cardFrame = GetComponent<CardFrame>();
        SlotNew slotSelectedSlotNew = FindObjectOfType<SlotNew>();
        slotSelected = slotSelectedSlotNew.GetComponent<SlotGeneric>();
		ReInitMinDistances();

	}

    // Update is called once per frame
    void Update()
    {
        isDragging = cardFrame.GetIsDragging();
        if (isDragging)
        {
            FindClosestSlotGeneric();
        }
    }

    void FindClosestSlotGeneric()
	{
		if(slotSell == null)
        {
			slotSell = FindObjectOfType<SlotSell>();
		}

		distanceToAnchor = (slotSell.transform.position - this.transform.position).sqrMagnitude;
		if(distanceToAnchor < minDistanceAnchor)
        {
			minDistanceAnchor = distanceToAnchor;
        }

		distanceToClosestSlot = Mathf.Infinity;
		closestSlot = null;
		allSlots = GameObject.FindObjectsOfType<SlotGeneric>();

		indexIter = 0;
		foreach (SlotGeneric currentSlot in allSlots)
		{
			distanceToSlot = (currentSlot.transform.position - this.transform.position).sqrMagnitude;
			if (distanceToSlot < distanceToClosestSlot)
			{
				distanceToClosestSlot = distanceToSlot;
				closestSlot = currentSlot;
			}
			if(currentSlot.slotNumber != 0 && distanceToSlot < minDistanceSlots[currentSlot.slotNumber - 1])
            {
				minDistanceSlots[currentSlot.slotNumber - 1] = distanceToSlot;
			}

			indexIter++; 
		}
		slotSelected = closestSlot;

	}

	public void ReInitMinDistances()
    {
		minDistanceSlots = new float[5] { 10000f, 10000f, 10000f, 10000f, 10000f };
		minDistanceAnchor = 10000f;
	}

	public SlotGeneric GetClosestSlot()
    {
		FindClosestSlotGeneric();
		return slotSelected;
    }

}
