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

package controller

import (
	"context"
	"fmt"
	"regexp"
	"strconv"
	"time"

	appsv1 "k8s.io/api/apps/v1"
	corev1 "k8s.io/api/core/v1"
	"k8s.io/apimachinery/pkg/api/errors"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime"
	"k8s.io/apimachinery/pkg/types"
	"k8s.io/apimachinery/pkg/util/intstr"
	ctrl "sigs.k8s.io/controller-runtime"
	"sigs.k8s.io/controller-runtime/pkg/client"
	"sigs.k8s.io/controller-runtime/pkg/controller/controllerutil"
	logf "sigs.k8s.io/controller-runtime/pkg/log"

	devserversv1 "github.com/seemethere/devserver/api/v1"
)

const (
	// DevServerFinalizer is the finalizer added to DevServer resources
	DevServerFinalizer = "devserver.devservers.io/finalizer"
)

// DevServerReconciler reconciles a DevServer object
type DevServerReconciler struct {
	client.Client
	Scheme *runtime.Scheme
}

// +kubebuilder:rbac:groups=apps.devservers.io,resources=devservers,verbs=get;list;watch;create;update;patch;delete
// +kubebuilder:rbac:groups=apps.devservers.io,resources=devservers/status,verbs=get;update;patch
// +kubebuilder:rbac:groups=apps.devservers.io,resources=devservers/finalizers,verbs=update
// +kubebuilder:rbac:groups=apps.devservers.io,resources=devserverflavors,verbs=get;list;watch
// +kubebuilder:rbac:groups="",resources=pods,verbs=get;list;watch;create;update;patch;delete
// +kubebuilder:rbac:groups="",resources=services,verbs=get;list;watch;create;update;patch;delete
// +kubebuilder:rbac:groups="",resources=persistentvolumeclaims,verbs=get;list;watch;create;update;patch;delete
// +kubebuilder:rbac:groups=apps,resources=deployments,verbs=get;list;watch;create;update;patch;delete

// Reconcile is part of the main kubernetes reconciliation loop which aims to
// move the current state of the cluster closer to the desired state.
func (r *DevServerReconciler) Reconcile(ctx context.Context, req ctrl.Request) (ctrl.Result, error) {
	log := logf.FromContext(ctx)

	// Fetch the DevServer instance
	devServer := &devserversv1.DevServer{}
	err := r.Get(ctx, req.NamespacedName, devServer)
	if err != nil {
		if errors.IsNotFound(err) {
			// Request object not found, could have been deleted after reconcile request
			log.Info("DevServer resource not found. Ignoring since object must be deleted")
			return ctrl.Result{}, nil
		}
		// Error reading the object - requeue the request
		log.Error(err, "Failed to get DevServer")
		return ctrl.Result{}, err
	}

	// Handle deletion
	if devServer.ObjectMeta.DeletionTimestamp.IsZero() {
		// The object is not being deleted, so if it does not have our finalizer,
		// then add the finalizer and update the object
		if !controllerutil.ContainsFinalizer(devServer, DevServerFinalizer) {
			controllerutil.AddFinalizer(devServer, DevServerFinalizer)
			return ctrl.Result{}, r.Update(ctx, devServer)
		}
	} else {
		// The object is being deleted
		if controllerutil.ContainsFinalizer(devServer, DevServerFinalizer) {
			// Our finalizer is present, so lets handle any external dependency
			if err := r.cleanupDevServer(ctx, devServer); err != nil {
				// If fail to delete the external dependency here, return with error
				// so that it can be retried
				return ctrl.Result{}, err
			}

			// Remove our finalizer from the list and update it
			controllerutil.RemoveFinalizer(devServer, DevServerFinalizer)
			if err := r.Update(ctx, devServer); err != nil {
				return ctrl.Result{}, err
			}
		}
		// Stop reconciliation as the item is being deleted
		return ctrl.Result{}, nil
	}

	// Main reconciliation logic
	return r.reconcileDevServer(ctx, devServer)
}

// cleanupDevServer handles cleanup when a DevServer is being deleted
func (r *DevServerReconciler) cleanupDevServer(ctx context.Context, devServer *devserversv1.DevServer) error {
	log := logf.FromContext(ctx)
	log.Info("Cleaning up DevServer resources", "devserver", devServer.Name)

	// Delete associated resources (Deployment, Service, PVCs)
	// Note: In a real implementation, you might want to preserve PVCs for data safety
	// depending on your use case

	// For now, just log the cleanup
	log.Info("DevServer cleanup completed", "devserver", devServer.Name)
	return nil
}

// reconcileDevServer handles the main reconciliation logic
func (r *DevServerReconciler) reconcileDevServer(ctx context.Context, devServer *devserversv1.DevServer) (ctrl.Result, error) {
	log := logf.FromContext(ctx)
	patch := client.MergeFrom(devServer.DeepCopy())
	log.Info("Reconciling DevServer", "devserver", devServer.Name, "mode", devServer.Spec.Mode)

	// Handle lifecycle and expiration
	if devServer.Spec.Lifecycle != nil {
		// If TimeToLive is set but ExpirationTime is not, calculate and set it.
		if devServer.Spec.Lifecycle.TimeToLive != "" && devServer.Spec.Lifecycle.ExpirationTime == nil {
			duration, err := parseDuration(devServer.Spec.Lifecycle.TimeToLive)
			if err != nil {
				log.Error(err, "Invalid TimeToLive duration", "timeToLive", devServer.Spec.Lifecycle.TimeToLive)
				// Set status to failed and don't requeue
				devServer.Status.Phase = "Failed"
				if err := r.Status().Patch(ctx, devServer, patch); err != nil {
					log.Error(err, "Failed to update DevServer status to Failed")
				}
				return ctrl.Result{}, nil // Stop reconciliation for this invalid spec
			}

			expirationTime := metav1.NewTime(devServer.CreationTimestamp.Time.Add(duration))
			devServer.Spec.Lifecycle.ExpirationTime = &expirationTime

			log.Info("Setting expiration time from TimeToLive", "expirationTime", expirationTime)
			if err := r.Update(ctx, devServer); err != nil {
				return ctrl.Result{}, err
			}
			return ctrl.Result{Requeue: true}, nil
		}

		// If ExpirationTime is set, check if we've passed it.
		if devServer.Spec.Lifecycle.ExpirationTime != nil {
			if time.Now().After(devServer.Spec.Lifecycle.ExpirationTime.Time) {
				log.Info("DevServer has expired, deleting.", "expirationTime", devServer.Spec.Lifecycle.ExpirationTime.Time)
				if err := r.Delete(ctx, devServer); err != nil {
					return ctrl.Result{}, err
				}
				// Deletion will trigger finalizer logic, so we can stop here.
				return ctrl.Result{}, nil
			}
		}
	}

	// Fetch the DevServerFlavor (cluster-scoped, no namespace)
	flavor := &devserversv1.DevServerFlavor{}
	flavorKey := types.NamespacedName{
		Name: devServer.Spec.Flavor,
		// No namespace - DevServerFlavor is cluster-scoped
	}
	if err := r.Get(ctx, flavorKey, flavor); err != nil {
		if errors.IsNotFound(err) {
			log.Error(err, "DevServerFlavor not found", "flavor", devServer.Spec.Flavor)
			// Update status to indicate the flavor is missing
			devServer.Status.Phase = "Failed"
			r.Status().Patch(ctx, devServer, patch)
			return ctrl.Result{RequeueAfter: time.Minute * 5}, nil
		}
		return ctrl.Result{}, err
	}

	// Smart requeue logic
	var requeueAfter time.Duration
	if devServer.Spec.Lifecycle != nil && devServer.Spec.Lifecycle.ExpirationTime != nil {
		requeueAfter = time.Until(devServer.Spec.Lifecycle.ExpirationTime.Time)
		if requeueAfter < 0 {
			requeueAfter = 0 // Expired, should be handled on next reconcile
		}
	}

	// Use a shorter requeue if expiration is near, otherwise default to 30 minutes
	defaultRequeue := 30 * time.Minute
	if requeueAfter <= 0 || requeueAfter > defaultRequeue {
		requeueAfter = defaultRequeue
	}

	// For now, only handle standalone mode (Phase 3 requirement)
	if devServer.Spec.Mode == "distributed" {
		log.Info("Distributed mode not yet implemented", "devserver", devServer.Name)
		devServer.Status.Phase = "Pending"
		r.Status().Patch(ctx, devServer, patch)
		return ctrl.Result{RequeueAfter: time.Minute * 5}, nil
	}

	// Handle standalone mode
	if err := r.reconcileStandaloneServer(ctx, devServer, flavor); err != nil {
		log.Error(err, "Failed to reconcile standalone server")
		devServer.Status.Phase = "Failed"
		r.Status().Patch(ctx, devServer, patch)
		return ctrl.Result{}, err
	}

	// Update status
	devServer.Status.Phase = "Running"
	devServer.Status.Ready = true
	if devServer.Status.StartTime == nil {
		now := metav1.Now()
		devServer.Status.StartTime = &now
	}

	if err := r.Status().Patch(ctx, devServer, patch); err != nil {
		log.Error(err, "Failed to update DevServer status")
		return ctrl.Result{}, err
	}

	log.Info("DevServer reconciliation completed", "devserver", devServer.Name, "requeueAfter", requeueAfter)
	return ctrl.Result{RequeueAfter: requeueAfter}, nil
}

// reconcileStandaloneServer creates/updates resources for a standalone DevServer
func (r *DevServerReconciler) reconcileStandaloneServer(ctx context.Context, devServer *devserversv1.DevServer, flavor *devserversv1.DevServerFlavor) error {
	log := logf.FromContext(ctx)

	// Create or update PVC for home directory
	if err := r.reconcilePVC(ctx, devServer); err != nil {
		return fmt.Errorf("failed to reconcile PVC: %w", err)
	}

	// Create or update Deployment
	if err := r.reconcileDeployment(ctx, devServer, flavor); err != nil {
		return fmt.Errorf("failed to reconcile Deployment: %w", err)
	}

	// Create or update Service (if SSH is enabled)
	if devServer.Spec.EnableSSH {
		if err := r.reconcileService(ctx, devServer); err != nil {
			return fmt.Errorf("failed to reconcile Service: %w", err)
		}
	}

	log.Info("Standalone server reconciliation completed", "devserver", devServer.Name)
	return nil
}

// reconcilePVC creates or updates the PVC for the DevServer home directory
func (r *DevServerReconciler) reconcilePVC(ctx context.Context, devServer *devserversv1.DevServer) error {
	pvcName := fmt.Sprintf("%s-home", devServer.Name)
	pvc := &corev1.PersistentVolumeClaim{}
	pvcKey := types.NamespacedName{Name: pvcName, Namespace: devServer.Namespace}

	err := r.Get(ctx, pvcKey, pvc)
	if err != nil {
		if errors.IsNotFound(err) {
			// PVC does not exist, create it
			newPvc := r.pvcForDevServer(devServer)
			if err := controllerutil.SetControllerReference(devServer, newPvc, r.Scheme); err != nil {
				return err
			}
			logf.FromContext(ctx).Info("Creating a new PVC", "PVC.Namespace", newPvc.Namespace, "PVC.Name", newPvc.Name)
			return r.Create(ctx, newPvc)
		}
		return err
	}

	// For PVCs, we generally don't update them once created,
	// but we can ensure the owner reference is set.
	patch := client.MergeFrom(pvc.DeepCopy())
	updated := false
	if metav1.GetControllerOf(pvc) == nil {
		if err := controllerutil.SetControllerReference(devServer, pvc, r.Scheme); err != nil {
			return err
		}
		updated = true
	}

	if updated {
		logf.FromContext(ctx).Info("Patching PVC with owner reference", "PVC.Namespace", pvc.Namespace, "PVC.Name", pvc.Name)
		return r.Patch(ctx, pvc, patch)
	}

	return nil
}

// pvcForDevServer returns a PVC object for the given DevServer
func (r *DevServerReconciler) pvcForDevServer(devServer *devserversv1.DevServer) *corev1.PersistentVolumeClaim {
	pvcName := fmt.Sprintf("%s-home", devServer.Name)
	return &corev1.PersistentVolumeClaim{
		ObjectMeta: metav1.ObjectMeta{
			Name:      pvcName,
			Namespace: devServer.Namespace,
		},
		Spec: corev1.PersistentVolumeClaimSpec{
			AccessModes: []corev1.PersistentVolumeAccessMode{
				corev1.ReadWriteOnce,
			},
			Resources: corev1.VolumeResourceRequirements{
				Requests: corev1.ResourceList{
					corev1.ResourceStorage: devServer.Spec.PersistentHomeSize,
				},
			},
		},
	}
}

// reconcileDeployment creates or updates the Deployment for the DevServer
func (r *DevServerReconciler) reconcileDeployment(ctx context.Context, devServer *devserversv1.DevServer, flavor *devserversv1.DevServerFlavor) error {
	deploymentName := devServer.Name
	deployment := &appsv1.Deployment{}
	deploymentKey := types.NamespacedName{Name: deploymentName, Namespace: devServer.Namespace}

	// Check if the deployment already exists
	err := r.Get(ctx, deploymentKey, deployment)
	if err != nil {
		if errors.IsNotFound(err) {
			// Deployment does not exist, create it
			newDeployment := r.deploymentForDevServer(devServer, flavor)
			if err := controllerutil.SetControllerReference(devServer, newDeployment, r.Scheme); err != nil {
				return err
			}
			logf.FromContext(ctx).Info("Creating a new Deployment", "Deployment.Namespace", newDeployment.Namespace, "Deployment.Name", newDeployment.Name)
			return r.Create(ctx, newDeployment)
		}
		return err // Some other error
	}

	// Deployment exists, create a patch from the existing deployment
	patch := client.MergeFrom(deployment.DeepCopy())

	// Mutate the deployment object with the desired state
	// Note: For a real-world operator, you'd have a more sophisticated update logic
	// here, carefully merging fields. For this example, we'll just re-apply the spec.
	updatedDeployment := r.deploymentForDevServer(devServer, flavor)
	deployment.Spec = updatedDeployment.Spec
	deployment.ObjectMeta.Labels = updatedDeployment.ObjectMeta.Labels // Example of updating metadata

	// Set owner reference just in case it's missing
	if err := controllerutil.SetControllerReference(devServer, deployment, r.Scheme); err != nil {
		return err
	}

	logf.FromContext(ctx).Info("Patching existing Deployment", "Deployment.Namespace", deployment.Namespace, "Deployment.Name", deployment.Name)
	return r.Patch(ctx, deployment, patch)
}

// deploymentForDevServer returns a Deployment object for the given DevServer
func (r *DevServerReconciler) deploymentForDevServer(devServer *devserversv1.DevServer, flavor *devserversv1.DevServerFlavor) *appsv1.Deployment {
	replicas := int32(1)
	labels := map[string]string{
		"app":       "devserver",
		"devserver": devServer.Name,
	}

	deployment := &appsv1.Deployment{
		ObjectMeta: metav1.ObjectMeta{
			Name:      devServer.Name,
			Namespace: devServer.Namespace,
			Labels:    labels,
		},
		Spec: appsv1.DeploymentSpec{
			Replicas: &replicas,
			Selector: &metav1.LabelSelector{
				MatchLabels: labels,
			},
			Template: corev1.PodTemplateSpec{
				ObjectMeta: metav1.ObjectMeta{
					Labels: labels,
				},
				Spec: corev1.PodSpec{
					Containers: []corev1.Container{
						{
							Name:    "devserver",
							Image:   devServer.Spec.Image,
							Command: []string{"sleep"},
							Args:    []string{"infinity"},
							Resources: corev1.ResourceRequirements{
								Requests: flavor.Spec.Resources.Requests,
								Limits:   flavor.Spec.Resources.Limits,
							},
							VolumeMounts: []corev1.VolumeMount{
								{
									Name:      "home",
									MountPath: "/home/dev",
								},
							},
							Env: []corev1.EnvVar{
								{
									Name:  "DEVSERVER_OWNER",
									Value: devServer.Spec.Owner,
								},
								{
									Name:  "DEVSERVER_MODE",
									Value: devServer.Spec.Mode,
								},
							},
						},
					},
					Volumes: []corev1.Volume{
						{
							Name: "home",
							VolumeSource: corev1.VolumeSource{
								PersistentVolumeClaim: &corev1.PersistentVolumeClaimVolumeSource{
									ClaimName: fmt.Sprintf("%s-home", devServer.Name),
								},
							},
						},
					},
					NodeSelector: flavor.Spec.NodeSelector,
					Tolerations:  flavor.Spec.Tolerations,
				},
			},
		},
	}

	// Add shared volume if specified
	if devServer.Spec.SharedVolumeClaimName != "" {
		deployment.Spec.Template.Spec.Containers[0].VolumeMounts = append(
			deployment.Spec.Template.Spec.Containers[0].VolumeMounts,
			corev1.VolumeMount{
				Name:      "shared",
				MountPath: "/shared",
			},
		)
		deployment.Spec.Template.Spec.Volumes = append(
			deployment.Spec.Template.Spec.Volumes,
			corev1.Volume{
				Name: "shared",
				VolumeSource: corev1.VolumeSource{
					PersistentVolumeClaim: &corev1.PersistentVolumeClaimVolumeSource{
						ClaimName: devServer.Spec.SharedVolumeClaimName,
					},
				},
			},
		)
	}

	return deployment
}

// reconcileService creates or updates the Service for SSH access
func (r *DevServerReconciler) reconcileService(ctx context.Context, devServer *devserversv1.DevServer) error {
	serviceName := fmt.Sprintf("%s-ssh", devServer.Name)
	service := &corev1.Service{}
	serviceKey := types.NamespacedName{Name: serviceName, Namespace: devServer.Namespace}

	err := r.Get(ctx, serviceKey, service)
	if err != nil {
		if errors.IsNotFound(err) {
			// Service does not exist, create it
			newService := r.serviceForDevServer(devServer)
			if err := controllerutil.SetControllerReference(devServer, newService, r.Scheme); err != nil {
				return err
			}
			logf.FromContext(ctx).Info("Creating a new Service", "Service.Namespace", newService.Namespace, "Service.Name", newService.Name)
			if err := r.Create(ctx, newService); err != nil {
				return err
			}
			// Update status after creation
			return r.updateDevServerStatusWithService(ctx, devServer, newService)
		}
		return err
	}

	// Service exists, patch if necessary
	patch := client.MergeFrom(service.DeepCopy())
	updated := false

	// Example of a mutable field: ensure labels are correct
	// In a real operator, you'd compare more fields.
	desiredLabels := r.serviceForDevServer(devServer).ObjectMeta.Labels
	if service.ObjectMeta.Labels == nil || service.ObjectMeta.Labels["app"] != desiredLabels["app"] {
		service.ObjectMeta.Labels = desiredLabels
		updated = true
	}

	if err := controllerutil.SetControllerReference(devServer, service, r.Scheme); err != nil {
		return err
	}

	if updated {
		logf.FromContext(ctx).Info("Patching existing Service", "Service.Namespace", service.Namespace, "Service.Name", service.Name)
		if err := r.Patch(ctx, service, patch); err != nil {
			return err
		}
	}

	return r.updateDevServerStatusWithService(ctx, devServer, service)
}

// serviceForDevServer returns a Service object for the given DevServer
func (r *DevServerReconciler) serviceForDevServer(devServer *devserversv1.DevServer) *corev1.Service {
	serviceName := fmt.Sprintf("%s-ssh", devServer.Name)
	labels := map[string]string{
		"app":       "devserver",
		"devserver": devServer.Name,
	}

	return &corev1.Service{
		ObjectMeta: metav1.ObjectMeta{
			Name:      serviceName,
			Namespace: devServer.Namespace,
			Labels:    labels,
		},
		Spec: corev1.ServiceSpec{
			Selector: labels,
			Ports: []corev1.ServicePort{
				{
					Name:       "ssh",
					Port:       22,
					TargetPort: intstr.FromInt(22),
					Protocol:   corev1.ProtocolTCP,
				},
			},
			Type: corev1.ServiceTypeClusterIP,
		},
	}
}

// updateDevServerStatusWithService updates the DevServer status with service details
func (r *DevServerReconciler) updateDevServerStatusWithService(ctx context.Context, devServer *devserversv1.DevServer, service *corev1.Service) error {
	patch := client.MergeFrom(devServer.DeepCopy())
	devServer.Status.SSHEndpoint = fmt.Sprintf("%s.%s.svc.cluster.local:22", service.Name, devServer.Namespace)
	devServer.Status.ServiceName = service.Name
	return r.Status().Patch(ctx, devServer, patch)
}

// parseDuration supports formats like "1d", "2h30m".
func parseDuration(s string) (time.Duration, error) {
	re := regexp.MustCompile(`(\d+)([dhms])`)
	matches := re.FindAllStringSubmatch(s, -1)
	if len(matches) == 0 {
		// Fallback to standard parser if our regex doesn't match
		return time.ParseDuration(s)
	}

	var totalDuration time.Duration
	for _, match := range matches {
		value, err := strconv.Atoi(match[1])
		if err != nil {
			return 0, err
		}
		unit := match[2]
		switch unit {
		case "d":
			totalDuration += time.Duration(value) * 24 * time.Hour
		case "h":
			totalDuration += time.Duration(value) * time.Hour
		case "m":
			totalDuration += time.Duration(value) * time.Minute
		case "s":
			totalDuration += time.Duration(value) * time.Second
		}
	}

	return totalDuration, nil
}

// SetupWithManager sets up the controller with the Manager.
func (r *DevServerReconciler) SetupWithManager(mgr ctrl.Manager) error {
	return ctrl.NewControllerManagedBy(mgr).
		For(&devserversv1.DevServer{}).
		Owns(&appsv1.Deployment{}).
		Owns(&corev1.Service{}).
		Owns(&corev1.PersistentVolumeClaim{}).
		Named("devserver").
		Complete(r)
}
