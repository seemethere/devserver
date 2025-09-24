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
	"k8s.io/apimachinery/pkg/api/resource"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
)

// EDIT THIS FILE!  THIS IS SCAFFOLDING FOR YOU TO OWN!
// NOTE: json tags are required.  Any new fields you add must have json tags for the fields to be serialized.

// DevServerSpec defines the desired state of DevServer
type DevServerSpec struct {
	// Owner specifies the email of the user who owns this DevServer
	// +required
	Owner string `json:"owner"`

	// Flavor references a DevServerFlavor resource that defines compute resources
	// +required
	Flavor string `json:"flavor"`

	// Image specifies the container image to use for the development server
	// +optional
	// +kubebuilder:default="company/pytorch-dev:latest"
	Image string `json:"image,omitempty"`

	// Mode specifies whether this is a standalone server or distributed training
	// +optional
	// +kubebuilder:default="standalone"
	// +kubebuilder:validation:Enum=standalone;distributed
	Mode string `json:"mode,omitempty"`

	// Distributed configuration for distributed training mode
	// +optional
	Distributed *DistributedConfig `json:"distributed,omitempty"`

	// PersistentHomeSize specifies the size of the persistent home directory volume
	// +optional
	// +kubebuilder:default="100Gi"
	PersistentHomeSize resource.Quantity `json:"persistentHomeSize,omitempty"`

	// SharedVolumeClaimName specifies the name of the shared EFS volume claim
	// +optional
	SharedVolumeClaimName string `json:"sharedVolumeClaimName,omitempty"`

	// EnableSSH enables SSH access to the development server
	// +optional
	// +kubebuilder:default=true
	EnableSSH bool `json:"enableSSH,omitempty"`

	// Lifecycle defines lifecycle management settings
	// +optional
	Lifecycle *LifecycleConfig `json:"lifecycle,omitempty"`
}

// DistributedConfig defines configuration for distributed PyTorch training
type DistributedConfig struct {
	// WorldSize specifies the total number of processes in distributed training
	// +required
	// +kubebuilder:validation:Minimum=1
	WorldSize int32 `json:"worldSize"`

	// NProcsPerNode specifies the number of processes per node
	// +optional
	// +kubebuilder:default=1
	// +kubebuilder:validation:Minimum=1
	NProcsPerNode int32 `json:"nprocsPerNode,omitempty"`

	// Backend specifies the distributed backend (nccl, gloo, mpi)
	// +optional
	// +kubebuilder:default="nccl"
	// +kubebuilder:validation:Enum=nccl;gloo;mpi
	Backend string `json:"backend,omitempty"`

	// NCCLSettings provides NCCL-specific configuration
	// +optional
	NCCLSettings map[string]string `json:"ncclSettings,omitempty"`
}

// LifecycleConfig defines lifecycle management settings
type LifecycleConfig struct {
	// IdleTimeout specifies how long (in seconds) the server can be idle before auto-shutdown
	// +optional
	// +kubebuilder:default=3600
	// +kubebuilder:validation:Minimum=60
	IdleTimeout int32 `json:"idleTimeout,omitempty"`

	// AutoShutdown enables automatic shutdown when idle timeout is reached
	// +optional
	// +kubebuilder:default=true
	AutoShutdown bool `json:"autoShutdown,omitempty"`
}

// DevServerStatus defines the observed state of DevServer.
type DevServerStatus struct {
	// Phase represents the current phase of the DevServer lifecycle
	// +optional
	// +kubebuilder:validation:Enum=Pending;Running;Terminating;Failed
	Phase string `json:"phase,omitempty"`

	// Ready indicates whether the DevServer is ready for use
	// +optional
	Ready bool `json:"ready,omitempty"`

	// SSHEndpoint provides the SSH connection information when SSH is enabled
	// +optional
	SSHEndpoint string `json:"sshEndpoint,omitempty"`

	// PodNames lists the names of pods created for this DevServer
	// +optional
	PodNames []string `json:"podNames,omitempty"`

	// ServiceName is the name of the service created for this DevServer
	// +optional
	ServiceName string `json:"serviceName,omitempty"`

	// LastIdleTime records the last time the server was detected as idle
	// +optional
	LastIdleTime *metav1.Time `json:"lastIdleTime,omitempty"`

	// StartTime records when the DevServer was started
	// +optional
	StartTime *metav1.Time `json:"startTime,omitempty"`

	// conditions represent the current state of the DevServer resource.
	// +listType=map
	// +listMapKey=type
	// +optional
	Conditions []metav1.Condition `json:"conditions,omitempty"`
}

// +kubebuilder:object:root=true
// +kubebuilder:subresource:status

// DevServer is the Schema for the devservers API
type DevServer struct {
	metav1.TypeMeta `json:",inline"`

	// metadata is a standard object metadata
	// +optional
	metav1.ObjectMeta `json:"metadata,omitempty,omitzero"`

	// spec defines the desired state of DevServer
	// +required
	Spec DevServerSpec `json:"spec"`

	// status defines the observed state of DevServer
	// +optional
	Status DevServerStatus `json:"status,omitempty,omitzero"`
}

// +kubebuilder:object:root=true

// DevServerList contains a list of DevServer
type DevServerList struct {
	metav1.TypeMeta `json:",inline"`
	metav1.ListMeta `json:"metadata,omitempty"`
	Items           []DevServer `json:"items"`
}

func init() {
	SchemeBuilder.Register(&DevServer{}, &DevServerList{})
}
