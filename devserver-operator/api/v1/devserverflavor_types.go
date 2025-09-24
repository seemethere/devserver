/*
Copyright 2025.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
*/

package v1

import (
	corev1 "k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
)

// EDIT THIS FILE!  THIS IS SCAFFOLDING FOR YOU TO OWN!
// NOTE: json tags are required.  Any new fields you add must have json tags for the fields to be serialized.

// DevServerFlavorSpec defines the desired state of DevServerFlavor
type DevServerFlavorSpec struct {
	// Resources defines the compute resources for this flavor
	// +required
	Resources ResourceRequirements `json:"resources"`

	// NodeSelector specifies node selection constraints for this flavor
	// +optional
	NodeSelector map[string]string `json:"nodeSelector,omitempty"`

	// Tolerations specifies tolerations for this flavor
	// +optional
	Tolerations []corev1.Toleration `json:"tolerations,omitempty"`
}

// ResourceRequirements defines resource requirements for DevServer pods
type ResourceRequirements struct {
	// Requests describes the minimum amount of compute resources required
	// +optional
	Requests corev1.ResourceList `json:"requests,omitempty"`

	// Limits describes the maximum amount of compute resources allowed
	// +optional
	Limits corev1.ResourceList `json:"limits,omitempty"`
}

// DevServerFlavorStatus defines the observed state of DevServerFlavor.
type DevServerFlavorStatus struct {
	// INSERT ADDITIONAL STATUS FIELD - define observed state of cluster
	// Important: Run "make" to regenerate code after modifying this file

	// For Kubernetes API conventions, see:
	// https://github.com/kubernetes/community/blob/master/contributors/devel/sig-architecture/api-conventions.md#typical-status-properties

	// conditions represent the current state of the DevServerFlavor resource.
	// Each condition has a unique type and reflects the status of a specific aspect of the resource.
	//
	// Standard condition types include:
	// - "Available": the resource is fully functional
	// - "Progressing": the resource is being created or updated
	// - "Degraded": the resource failed to reach or maintain its desired state
	//
	// The status of each condition is one of True, False, or Unknown.
	// +listType=map
	// +listMapKey=type
	// +optional
	Conditions []metav1.Condition `json:"conditions,omitempty"`
}

// +kubebuilder:object:root=true
// +kubebuilder:subresource:status
// +kubebuilder:resource:scope=Cluster

// DevServerFlavor is the Schema for the devserverflavors API
type DevServerFlavor struct {
	metav1.TypeMeta `json:",inline"`

	// metadata is a standard object metadata
	// +optional
	metav1.ObjectMeta `json:"metadata,omitempty,omitzero"`

	// spec defines the desired state of DevServerFlavor
	// +required
	Spec DevServerFlavorSpec `json:"spec"`

	// status defines the observed state of DevServerFlavor
	// +optional
	Status DevServerFlavorStatus `json:"status,omitempty,omitzero"`
}

// +kubebuilder:object:root=true

// DevServerFlavorList contains a list of DevServerFlavor
type DevServerFlavorList struct {
	metav1.TypeMeta `json:",inline"`
	metav1.ListMeta `json:"metadata,omitempty"`
	Items           []DevServerFlavor `json:"items"`
}

func init() {
	SchemeBuilder.Register(&DevServerFlavor{}, &DevServerFlavorList{})
}
